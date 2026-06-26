"""Shared DNS data models and proxy helper utilities.

Defines the RECORD_TYPE literal, DNSRecord and DNSRecordQueryKey
dataclasses used across DNS provider implementations, and a
ProxyHelper class for managing SOCKS5 proxy environment variables.
"""

import os
import logging
from typing import Literal
from dataclasses import dataclass


RECORD_TYPE = Literal["A", "AAAA", "CNAME", "MX", "NS", "SOA", "SRV", "TXT"]
"""Type alias for supported DNS record types."""


@dataclass
class DNSRecordQueryKey:
    """Composite key for looking up a DNS record.

    :var name: The record name (subdomain or ``@`` for the root).
    :vartype name: str
    :var type: The DNS record type (e.g. ``"A"``, ``"AAAA"``).
    :vartype type: RECORD_TYPE
    """

    name: str = ""
    type: RECORD_TYPE = "TXT"


@dataclass
class DNSRecord:
    """Represents a single DNS resource record.

    Used as the shared data transfer object between the abstract API
    layer and concrete provider implementations.

    :var id: Provider-specific record identifier.
    :vartype id: str
    :var domain: The base domain (e.g. ``example.com``).
    :vartype domain: str
    :var name: The record name / subdomain.
    :vartype name: str
    :var type: DNS record type.
    :vartype type: RECORD_TYPE
    :var value: The record content / value.
    :vartype value: str
    :var ttl: Time-to-live in seconds.
    :vartype ttl: int
    :var comment: Optional descriptive comment.
    :vartype comment: str
    """

    id: str = ""
    domain: str = ""
    name: str = ""
    type: RECORD_TYPE = "TXT"
    value: str = ""
    ttl: int = 600
    comment: str = ""


class ProxyHelper:
    """Manages the ``ALL_PROXY`` environment variable for SOCKS5 proxy support."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def set_proxy(self, proxy: str = "socks5://localhost:10808"):
        """Enable a SOCKS5 proxy by setting the ``ALL_PROXY`` env var.

        :param proxy: Proxy URL (default ``socks5://localhost:10808``).
        :type proxy: str
        """
        self.logger.warning("Setting proxy service...")
        os.environ["ALL_PROXY"] = proxy
        self.logger.warning(f"Proxy service set as \"{os.environ.get('ALL_PROXY')}\"!")

    def unset_proxy(self):
        """Disable the proxy by removing the ``ALL_PROXY`` env var."""
        self.logger.warning("Removing proxy service...")
        if os.environ.get("ALL_PROXY") is not None:
            os.environ.pop("ALL_PROXY")
        self.logger.warning("Proxy service removed!")
