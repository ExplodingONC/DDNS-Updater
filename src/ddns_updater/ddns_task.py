"""Core DDNS task logic for IP detection and DNS record synchronization.

Defines the DDNSTask class which runs an infinite loop comparing local
IP addresses against remote DNS records and pushing updates when they
differ.
"""

import time
from dataclasses import dataclass

import logging

from .interface_handlers import Localhost, UnifiGateway

from .dns_api import RECORD_TYPE, AbstractDNSApi, AbstractDNSConfig
from .dns_api.utils import DNSRecord
from .config_loader import DDNSTaskConfig, UniFiCredentials


@dataclass
class DDNSTaskTracker:
    """Tracks local and remote DNS record state for a single task.

    :var local_record: The DNS record derived from the local IP source.
    :vartype local_record: DNSRecord
    :var remote_record: The current DNS record from the provider API.
    :vartype remote_record: DNSRecord
    :var config: The task configuration this tracker belongs to.
    :vartype config: DDNSTaskConfig
    """

    local_record: DNSRecord
    remote_record: DNSRecord | None
    config: DDNSTaskConfig


def _parse_source(source: str) -> tuple[str, str]:
    """Parse a source string into a kind and optional interface name.

    :param source: A string like ``"local.eno4"``.
    :type source: str
    :returns: A tuple of ``(kind, interface)`` where *interface* is empty
        when no dot is present.
    :rtype: tuple[str, str]
    :raises ValueError: If a dot is present but no interface name follows.
    """
    if "." in source:
        kind, interface = source.split(".", 1)
        if not interface:
            raise ValueError(f"Interface name required in source '{source}'")
        return kind, interface
    return source, ""


class DDNSTask:
    """Manages DNS record monitoring and updates for a single DNS target.

    Each instance is associated with one DNS provider domain and runs
    an infinite loop that checks local IP addresses against the remote
    DNS records, pushing updates when differences are detected.

    :param api_config: Provider-specific DNS configuration.
    :type api_config: AbstractDNSConfig
    :param task_configs: List of record-level task configurations.
    :type task_configs: list[DDNSTaskConfig]
    """

    task_configs: list[DDNSTaskConfig]

    def __init__(self, api_config: AbstractDNSConfig, task_configs: list[DDNSTaskConfig]) -> None:
        self.domain: str = api_config.domain
        self.task_name = (api_config.handler_class.__name__.rstrip("DNSApi")
                          + "@\"" + api_config.domain + "\"")
        self.logger = logging.getLogger(__name__)
        self.logger.warning(f"DDNS task <{self.task_name}> created!")

        self.api_handler: AbstractDNSApi = api_config.handler_class(api_config)

        self.task_configs = task_configs
        self.tasks: list[DDNSTaskTracker] = []
        self._local_handlers: dict[str, Localhost] = {}
        self._unifi_handlers: dict[str, UnifiGateway] = {}

        for task_config in self.task_configs:
            record_args = {"domain": self.domain, "name": task_config.name, "type": task_config.type}
            self.tasks.append(DDNSTaskTracker(local_record=DNSRecord(**record_args),
                                              remote_record=DNSRecord(**record_args),
                                              config=task_config))

            kind, interface = _parse_source(task_config.source)
            if kind == "local" and interface and interface not in self._local_handlers:
                self._local_handlers[interface] = Localhost(interface=interface)
            elif kind == "unifi":
                site_name = interface or "default"
                if site_name not in self._unifi_handlers:
                    if not task_config.unifi_credentials:
                        self.logger.warning(
                            f"UniFi credentials required for source '{task_config.source}'"
                        )
                        continue
                    self._unifi_handlers[site_name] = UnifiGateway(
                        controller_url=task_config.unifi_credentials.controller_url,
                        username=task_config.unifi_credentials.username,
                        password=task_config.unifi_credentials.password,
                        site_name=site_name,
                    )

    def fetch_dns_record(self, task_tracker: DDNSTaskTracker):
        """Fetch the current remote DNS record for a task tracker.

        Updates ``task_tracker.remote_record`` in place with the result
        from the provider API. It is set to ``None`` when no record exists,
        when the provider call failed, or when several records share the
        name and type — duplicates make the remote state ambiguous, and
        clearing the tracker turns the next comparison into an update,
        which collapses them back to a single record.
        """
        records = self.api_handler.get_records(name=task_tracker.config.name,
                                               type=task_tracker.config.type)
        if records is None:
            self.logger.warning(f"Remote state of {task_tracker.config.type} record for "
                                f"{task_tracker.config.name} is unknown")
            task_tracker.remote_record = None
        elif len(records) > 1:
            self.logger.warning(f"Found {len(records)} duplicate {task_tracker.config.type} records "
                                f"for {task_tracker.config.name}, an update will collapse them into one")
            task_tracker.remote_record = None
        else:
            task_tracker.remote_record = records[0] if records else None

    def push_dns_record(self, task_tracker: DDNSTaskTracker):
        """Push the local record to the DNS provider and refresh the remote state."""

        self.api_handler.set_record(record=task_tracker.local_record)
        self.fetch_dns_record(task_tracker)

    def remove_dns_record(self, task_tracker: DDNSTaskTracker):
        """Delete the remote DNS record and refresh the remote state."""

        self.api_handler.delete_record(name=task_tracker.config.name,
                                       type=task_tracker.config.type)
        self.fetch_dns_record(task_tracker)

    def main(self):
        """Execute one iteration of the DDNS monitoring loop.

        Iterates through all task trackers, compares local IP addresses
        against remote DNS records, and pushes updates or removes stale
        records as needed.
        """

        # iter through all tasks (different target records)
        for task_tracker in self.tasks:

            kind, interface = _parse_source(task_tracker.config.source)

            if kind == "local":

                local_handler = self._local_handlers[interface]

                if task_tracker.config.type == "A":
                    current_ipv4 = local_handler.get_ipv4_ip()
                    if current_ipv4 is None:
                        self.logger.warning("Local IPv4 address not available")
                        continue
                    task_tracker.local_record.value = str(current_ipv4)
                    self.logger.info(f"Local IPv4 address is {current_ipv4} "
                                    f"({'is' if current_ipv4.is_private else 'not'} private)")
                    if not current_ipv4.is_private:
                        if task_tracker.remote_record is None or str(current_ipv4) != task_tracker.remote_record.value:
                            self.logger.warning(f"DDNS update for IPv4 is needed...")
                            self.push_dns_record(task_tracker=task_tracker)
                        else:
                            self.logger.info(f"DDNS for IPv4 is up to date...")

                elif task_tracker.config.type == "AAAA":
                    current_ipv6 = local_handler.get_ipv6_ip()
                    if current_ipv6 is None:
                        self.logger.warning("Local IPv6 address not available")
                        continue
                    task_tracker.local_record.value = str(current_ipv6)
                    self.logger.info(f"Local IPv6 address is {current_ipv6} "
                                    f"({'is' if current_ipv6.is_private else 'not'} private)")
                    if not current_ipv6.is_private:
                        if task_tracker.remote_record is None or str(current_ipv6) != task_tracker.remote_record.value:
                            self.logger.warning(f"DDNS update for IPv6 is needed...")
                            self.push_dns_record(task_tracker=task_tracker)
                        else:
                            self.logger.info(f"DDNS for IPv6 is up to date...")

            elif kind == "unifi":
                site_name = interface or "default"
                unifi_handler = self._unifi_handlers.get(site_name)
                if not unifi_handler:
                    self.logger.warning(f"UniFi handler for site '{site_name}' not available")
                    continue

                if task_tracker.config.type == "A":
                    current_ipv4 = unifi_handler.get_ipv4_ip()
                    if current_ipv4 is None:
                        self.logger.warning("UniFi gateway IPv4 address not available")
                        continue
                    task_tracker.local_record.value = str(current_ipv4)
                    self.logger.info(f"UniFi gateway IPv4 address is {current_ipv4} "
                                    f"({'is' if current_ipv4.is_private else 'not'} private)")
                    if not current_ipv4.is_private:
                        if task_tracker.remote_record is None or str(current_ipv4) != task_tracker.remote_record.value:
                            self.logger.warning(f"DDNS update for IPv4 is needed...")
                            self.push_dns_record(task_tracker=task_tracker)
                        else:
                            self.logger.info(f"DDNS for IPv4 is up to date...")

                elif task_tracker.config.type == "AAAA":
                    current_ipv6 = unifi_handler.get_ipv6_ip()
                    if current_ipv6 is None:
                        self.logger.warning("UniFi gateway IPv6 address not available")
                        continue
                    task_tracker.local_record.value = str(current_ipv6)
                    self.logger.info(f"UniFi gateway IPv6 address is {current_ipv6} "
                                    f"({'is' if current_ipv6.is_private else 'not'} private)")
                    if not current_ipv6.is_private:
                        if task_tracker.remote_record is None or str(current_ipv6) != task_tracker.remote_record.value:
                            self.logger.warning(f"DDNS update for IPv6 is needed...")
                            self.push_dns_record(task_tracker=task_tracker)
                        else:
                            self.logger.info(f"DDNS for IPv6 is up to date...")

    def run(self):
        """Run the DDNS monitoring loop indefinitely.

        Executes ``main()`` every 60 seconds. Catches and logs all
        exceptions to keep the loop alive.
        """
        while True:
            try:
                self.main()
                time.sleep(60)
            except Exception as e:
                self.logger.warning(f"DDNS update attempt failed: {e}")
                self.logger.exception(e)
