"""Local IP detection via psutil network interface queries.

Provides the Localhost class which reads IPv4 and IPv6 addresses
from a specified network interface on the local machine.
"""

import logging
import socket
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

    def get_ipv6_ip(self) -> Optional[ipaddress.IPv6Address]:
        """Return the IPv6 address of the configured interface.

        :returns: The interface's IPv6 address, or ``None`` if no
            IPv6 address is assigned.
        :rtype: ipaddress.IPv6Address | None
        """

        try:
            addrs = psutil.net_if_addrs()[self.interface]
            return ipaddress.IPv6Address(next(a.address for a in addrs if a.family == socket.AF_INET6))
        except Exception as e:
            self.logger.warning(f"Unable to get IPv6 IP from localhost:\n"
                                f"{e}")
            return None
