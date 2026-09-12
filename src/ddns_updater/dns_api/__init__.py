"""DNS provider API abstractions and implementations.

Exports the abstract base classes (AbstractDNSConfig, AbstractDNSApi),
the RECORD_TYPE literal, and the Cloudflare DNS provider implementation.
"""

from .utils import RECORD_TYPE
from .abstract_api import AbstractDNSConfig, AbstractDNSApi
from .cloudflare_api import CloudflareDNSConfig, CloudflareDNSApi
