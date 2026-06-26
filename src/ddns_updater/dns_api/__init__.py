"""DNS provider API abstractions and implementations.

Exports the abstract base classes (AbstractDNSConfig, AbstractDNSApi),
the RECORD_TYPE literal, and concrete implementations for Cloudflare
and GoDaddy DNS providers.
"""

from .utils import RECORD_TYPE
from .abstract_api import AbstractDNSConfig, AbstractDNSApi
from .godaddy_api import GodaddyDNSConfig, GodaddyDNSApi
from .cloudflare_api import CloudflareDNSConfig, CloudflareDNSApi
