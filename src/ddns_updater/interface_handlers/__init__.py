"""Interface handlers for obtaining IP addresses from various sources.

Provides an abstract base class (AbstractInterfaceHandler) and a concrete
implementation for local network interfaces (Localhost).
"""

from .abstract_handler import AbstractInterfaceHandler
from .localhost import Localhost

__all__ = ["AbstractInterfaceHandler", "Localhost"]
