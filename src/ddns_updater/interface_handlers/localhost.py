"""Local IP detection via psutil network interface queries.

Provides the Localhost class which reads IPv4 and IPv6 addresses
from a specified network interface on the local machine.
"""

import logging
import re
import socket
import subprocess
import ipaddress
from typing import Optional
import psutil
from .abstract_handler import AbstractInterfaceHandler


class Localhost(AbstractInterfaceHandler):
    """Reads IP addresses from a local network interface using psutil.

    :param interface: Name of the network interface (e.g. ``"eth0"``,
        ``"eno4"``). Must exist on the local machine.
    :type interface: str
    :raises ValueError: If the specified interface does not exist.
    :var interface: The validated network interface name.
    :vartype interface: str
    """

    def __init__(self, interface: str) -> None:
        self.logger = logging.getLogger(__name__)
        if interface not in psutil.net_if_addrs():
            raise ValueError(f"Network interface '{interface}' not found")
        self.interface = interface

    def get_ipv4_ip(self) -> Optional[ipaddress.IPv4Address]:
        """Return the IPv4 address of the configured interface.

        :returns: The interface's IPv4 address, or ``None`` if no
            IPv4 address is assigned.
        :rtype: ipaddress.IPv4Address | None
        """

        try:
            addrs = psutil.net_if_addrs()[self.interface]
            return ipaddress.IPv4Address(next(a.address for a in addrs if a.family == socket.AF_INET))
        except Exception as e:
            self.logger.warning(f"Unable to get IPv4 IP from localhost:\n"
                                f"{e}")
            return None

    def _get_ipv6_candidates(self) -> list[tuple[ipaddress.IPv6Address, int]]:
        """Parse ``ip -6 addr show`` to get global IPv6 addresses with lifetimes.

        :returns: A list of ``(address, valid_lft_seconds)`` tuples for
            global-scope non-link-local addresses, sorted by descending
            remaining lifetime.
        :rtype: list[tuple[ipaddress.IPv6Address, int]]
        """
        result = subprocess.run(
            ["ip", "-6", "addr", "show", "dev", self.interface],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.splitlines()
        candidates: list[tuple[ipaddress.IPv6Address, int]] = []
        i = 0
        while i < len(lines):
            m = re.match(
                r'\s+inet6\s+([0-9a-f:]+)/\d+\s+scope\s+(\w+)',
                lines[i],
            )
            if m:
                addr_str, scope = m.group(1), m.group(2)
                valid_lft = 0
                if i + 1 < len(lines):
                    lft_m = re.search(r'valid_lft\s+(\d+)sec', lines[i + 1])
                    if lft_m:
                        valid_lft = int(lft_m.group(1))
                    elif 'valid_lft forever' in lines[i + 1]:
                        valid_lft = 2**32
                if scope == 'global' and not addr_str.startswith('fe80:'):
                    try:
                        candidates.append(
                            (ipaddress.IPv6Address(addr_str), valid_lft)
                        )
                    except ValueError:
                        pass
            i += 1
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    def get_ipv6_ip(self) -> Optional[ipaddress.IPv6Address]:
        """Return the best IPv6 address of the configured interface.

        Picks the global-scope address with the longest remaining
        ``valid_lft`` (i.e. the most recently assigned prefix). Falls
        back to ``psutil`` if ``ip`` output parsing yields no result.

        :returns: The interface's IPv6 address, or ``None`` if no
            IPv6 address is assigned.
        :rtype: ipaddress.IPv6Address | None
        """
        try:
            candidates = self._get_ipv6_candidates()
            if candidates:
                best = candidates[0][0]
                self.logger.info(
                    f"Best IPv6 candidate: {best} "
                    f"(valid_lft {candidates[0][1]}s, "
                    f"{len(candidates)} candidates total)"
                )
                return best
        except Exception as e:
            self.logger.warning(
                f"ip command failed, falling back to psutil: {e}"
            )

        try:
            addrs = psutil.net_if_addrs()[self.interface]
            return ipaddress.IPv6Address(
                next(a.address for a in addrs if a.family == socket.AF_INET6)
            )
        except Exception as e:
            self.logger.warning(
                f"Unable to get IPv6 IP from localhost:\n{e}"
            )
            return None
