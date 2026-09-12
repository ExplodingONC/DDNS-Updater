"""Abstract base classes for DNS provider configuration and API access.

Defines ``AbstractDNSConfig`` (the dataclass base for provider-specific
configuration) and ``AbstractDNSApi`` (the ABC that all DNS provider
implementations must subclass).
"""

from __future__ import annotations
from abc import abstractmethod, ABC
from dataclasses import dataclass
import logging
from .utils import RECORD_TYPE, DNSRecord


@dataclass
class AbstractDNSConfig:
    """Base configuration dataclass for DNS providers.

    Concrete provider configs (e.g. ``CloudflareDNSConfig``) inherit
    from this class and add provider-specific fields such as API keys.

    :var handler_class: The ``AbstractDNSApi`` subclass to instantiate.
    :vartype handler_class: AbstractDNSApi
    :var domain: The DNS domain to manage (e.g. ``example.com``).
    :vartype domain: str
    :var timeout: HTTP request timeout in seconds.
    :vartype timeout: float
    """

    handler_class: type[AbstractDNSApi] = None
    domain: str = ""
    timeout: float = 10

    def dict(self):
        """Return the configuration as a plain dictionary."""
        return self.__dict__


class AbstractDNSApi(ABC):
    """Abstract interface for DNS record CRUD operations.

    Each concrete implementation wraps a specific provider's REST API
    and translates between ``DNSRecord`` objects and provider-native
    request/response formats.

    :param config: Provider-specific configuration (must be or extend
        ``AbstractDNSConfig``).
    :type config: AbstractDNSConfig
    """

    def __init__(self, config: AbstractDNSConfig):
        self.domain = config.domain
        self.timeout = config.timeout
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def list_all_records(self) -> list[DNSRecord]:
        """List all DNS records for the configured domain.

        :returns: A list of ``DNSRecord`` objects.
        :rtype: list[DNSRecord]
        """
        pass

    @abstractmethod
    def get_record(self, name: str, type: RECORD_TYPE) -> DNSRecord | None:
        """Retrieve a single DNS record by name and type.

        :param name: Record name (subdomain).
        :type name: str
        :param type: DNS record type.
        :type type: RECORD_TYPE
        :returns: A ``DNSRecord`` or ``None`` if not found.
        :rtype: DNSRecord | None
        """
        pass

    @abstractmethod
    def set_record(self, record: DNSRecord) -> bool:
        """Create or update a DNS record.

        If a record with the same name and type already exists it is
        updated; otherwise a new record is created.

        :param record: The ``DNSRecord`` to upsert.
        :type record: DNSRecord
        :returns: ``True`` on success, ``False`` on failure.
        :rtype: bool
        """
        pass

    @abstractmethod
    def delete_record(self, name: str, type: RECORD_TYPE) -> bool:
        """Delete a DNS record by name and type.

        :param name: Record name (subdomain).
        :type name: str
        :param type: DNS record type.
        :type type: RECORD_TYPE
        :returns: ``True`` on success, ``False`` on failure or if the record
            does not exist.
        :rtype: bool
        """
        pass
