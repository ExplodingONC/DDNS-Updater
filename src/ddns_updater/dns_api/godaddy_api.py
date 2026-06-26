"""GoDaddy DNS API implementation.

Provides ``GodaddyDNSConfig`` (extending ``AbstractDNSConfig`` with
GoDaddy API key/secret credentials) and ``GodaddyDNSApi`` which uses
the GoDaddy REST API to perform DNS record CRUD operations. Supports
optional SOCKS5 proxy routing.
"""

import requests
from dataclasses import dataclass
from .utils import RECORD_TYPE, DNSRecord
from .abstract_api import AbstractDNSConfig, AbstractDNSApi


@dataclass
class GodaddyDNSConfig(AbstractDNSConfig):
    """Configuration for the GoDaddy DNS provider.

    :var handler_class: The API handler class (``GodaddyDNSApi``).
    :vartype handler_class: AbstractDNSApi
    :var use_proxy: Whether to route requests through a SOCKS5 proxy.
    :vartype use_proxy: bool
    :var key: GoDaddy API key.
    :vartype key: str
    :var secret: GoDaddy API secret.
    :vartype secret: str
    """

    handler_class: AbstractDNSApi = None
    use_proxy: bool = True
    key: str = ""
    secret: str = ""


class GodaddyDNSApi(AbstractDNSApi):
    """GoDaddy DNS record management via the GoDaddy REST API.

    :param config: GoDaddy-specific configuration.
    :type config: GodaddyDNSConfig
    """

    def __init__(self, config: GodaddyDNSConfig):
        super().__init__(config)
        self.key: str = config.key
        self.secret: str = config.secret
        self.headers: dict = {"Accept": "application/json",
                              "Content-Type": "application/json",
                              "Authorization": f"sso-key {self.key}:{self.secret}"}

    def list_all_records(self) -> list[DNSRecord]:
        """List all DNS records for the configured domain.

        :returns: A list of ``DNSRecord`` objects.
        :rtype: list[DNSRecord]
        """
        uri = f"https://api.godaddy.com/v1/domains/{self.domain}/records"
        response = requests.get(url=uri,
                                headers=self.headers,
                                timeout=self.timeout)
        try:
            if response.status_code == 200:
                self.logger.info(f"Succeeded to list all records for {self.domain}")
                response_json = response.json()
                self.logger.debug(f"Got {len(response_json)} result(s)")
                records = []
                for result in response_json:
                    records.append(DNSRecord(
                        domain=self.domain,
                        name=result["name"],
                        type=result["type"],  # type: ignore[assignment]
                        value=result["data"],
                        ttl=result["ttl"],
                    ))
                return records
            else:
                self.logger.warning(f"Failed to list records for {self.domain}:\n"
                                    f"Status Code: {response.status_code}\n"
                                    f"Json Content: {response.json()}")
                return []
        except Exception as e:
            self.logger.warning(f"Failed to list records for {self.domain}:\n"
                                f"Status Code: {response.status_code}\n"
                                f"Json Content: {response.json()}\n"
                                f"Exception: {e}")
            return []

    def get_record(self, name: str, type: RECORD_TYPE) -> DNSRecord | None:
        """Fetch a DNS record from GoDaddy by name and type.

        :param name: Record name (subdomain).
        :type name: str
        :param type: DNS record type.
        :type type: RECORD_TYPE
        :returns: A ``DNSRecord`` populated from the API response, or
            ``None`` if the record is not found or an error occurs.
        :rtype: DNSRecord | None
        """
        uri = (f"https://api.godaddy.com/v1/domains/{self.domain}/"
               f"records/{type}/{name}")
        response = requests.get(url=uri,
                                headers=self.headers,
                                timeout=self.timeout)
        try:
            if response.status_code == 200:
                self.logger.info(f"Succeeded to get {type} record for {name}")
                response_json = response.json()
                self.logger.debug(response_json)
                if len(response_json) > 0:
                    result = response_json[0]
                    return DNSRecord(domain=self.domain, name=name, type=type,
                                     value=result["data"],
                                     ttl=result["ttl"])
                else:
                    self.logger.warning(f"No {type} record is found for {name}")
                    return None
            else:
                self.logger.warning(f"Failed to fetch {type} record for {name}:\n"
                                    f"Status Code: {response.status_code}\n"
                                    f"Json Content: {response.json()}")
                return None
        except Exception as e:
            self.logger.warning(f"Failed to fetch {type} record for {name}:\n"
                                f"Status Code: {response.status_code}\n"
                                f"Json Content: {response.json()}\n"
                                f"Exception: {e}")
            return None

    def set_record(self, record: DNSRecord) -> bool:
        """Create or update a DNS record on GoDaddy.

        Uses a PUT request which replaces the existing record of the
        given name and type, or creates a new one.

        :param record: The ``DNSRecord`` to upsert.
        :type record: DNSRecord
        :returns: ``True`` on success, ``False`` on failure.
        :rtype: bool
        """
        uri = (f"https://api.godaddy.com/v1/domains/{self.domain}/"
               f"records/{record.type}/{record.name}")
        payload = [{"data": record.value, "ttl": record.ttl}]
        response = requests.put(url=uri,
                                headers=self.headers,
                                json=payload,
                                timeout=self.timeout)
        try:
            if response.status_code == 200:
                return True
            else:
                self.logger.warning(f"Failed to set {record.type} record for {record.name} as {record.value}:\n"
                                    f"Status Code: {response.status_code}\n"
                                    f"Json Content: {response.json()}")
                return False
        except Exception as e:
            self.logger.warning(f"Failed to set {record.type} record for {record.name} as {record.value}:\n"
                                f"Status Code: {response.status_code}\n"
                                f"Json Content: {response.json()}\n"
                                f"Exception: {e}")
            return False
        
    def delete_record(self, name: str, type: RECORD_TYPE) -> bool:
        """Delete a DNS record from GoDaddy by name and type.

        :param name: Record name (subdomain).
        :type name: str
        :param type: DNS record type.
        :type type: RECORD_TYPE
        :returns: ``True`` on success, ``False`` on failure.
        :rtype: bool
        """
        uri = (f"https://api.godaddy.com/v1/"
               f"domains/{self.domain}/"
               f"records/{type}/{name}")
        response = requests.delete(url=uri,
                                   headers=self.headers,
                                   timeout=self.timeout)
        try:
            if response.status_code == 204:
                self.logger.info(f"Succeeded to delete {type} record for {name}")
                return True
            else:
                self.logger.warning(f"Failed to delete {type} record for {name}:\n"
                                    f"Status Code: {response.status_code}\n"
                                    f"Json Content: {response.json()}")
                return False
        except Exception as e:
            self.logger.warning(f"Failed to delete {type} record for {name}:\n"
                                f"Status Code: {response.status_code}\n"
                                f"Json Content: {response.json()}\n"
                                f"Exception: {e}")
            return False
