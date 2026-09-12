"""Interface handlers for obtaining IP addresses from various sources.

Provides an abstract base class (AbstractInterfaceHandler) and concrete
implementations for local network interfaces (Localhost) and UniFi
gateways (UnifiGateway).
"""

from .abstract_handler import AbstractInterfaceHandler
from .localhost import Localhost
from .unifi_gateway import UnifiGateway

__all__ = ["AbstractInterfaceHandler", "Localhost", "UnifiGateway"]
