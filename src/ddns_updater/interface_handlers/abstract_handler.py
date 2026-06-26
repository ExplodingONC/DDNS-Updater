"""Abstract base class for network interface IP handlers.

Defines the ``AbstractInterfaceHandler`` interface that all IP source
implementations must conform to.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
import ipaddress


class AbstractInterfaceHandler(ABC):
    """Abstract interface for retrieving IPv4 and IPv6 addresses.

    Concrete implementations query a specific IP source (e.g. a local
    network interface) and return the addresses as ``ipaddress`` objects.
    """

    @abstractmethod
    def get_ipv4_ip(self) -> Optional[ipaddress.IPv4Address]:
        """Return the IPv4 address from this interface handler.

        :returns: An ``IPv4Address`` or ``None`` if no valid address
            is available.
        :rtype: ipaddress.IPv4Address | None
        """

        pass

    @abstractmethod
    def get_ipv6_ip(self) -> Optional[ipaddress.IPv6Address]:
        """Return the IPv6 address from this interface handler.

        :returns: An ``IPv6Address`` or ``None`` if no valid address
            is available.
        :rtype: ipaddress.IPv6Address | None
        """

        pass
