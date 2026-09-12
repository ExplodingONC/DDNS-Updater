"""Shared DNS data models and utilities.

Defines the RECORD_TYPE literal and DNSRecord dataclass used across
DNS provider implementations.
"""

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
