"""Cloudflare DNS API implementation.

Provides ``CloudflareDNSConfig`` (extending ``AbstractDNSConfig`` with
Cloudflare-specific credentials) and ``CloudflareDNSApi`` which uses
the ``cloudflare`` Python SDK to perform DNS record CRUD operations.
"""

import cloudflare
from dataclasses import dataclass
from cloudflare import Cloudflare
from .utils import RECORD_TYPE, DNSRecord
from .abstract_api import AbstractDNSConfig, AbstractDNSApi


@dataclass
class CloudflareDNSConfig(AbstractDNSConfig):
    """Configuration for the Cloudflare DNS provider.

    :var handler_class: The API handler class (``CloudflareDNSApi``).
    :vartype handler_class: AbstractDNSApi
    :var api_token: Cloudflare API token (User ``cfut_`` or Account ``cfat_``).
        Mutually exclusive with email/api_key.
    :vartype api_token: str
    :var email: Account email for Global API Key auth.
        Mutually exclusive with api_token.
    :vartype email: str
    :var api_key: Global API Key (``cfk_``) for Account API auth.
        Mutually exclusive with api_token.
    :vartype api_key: str
    :var zone_id: Cloudflare zone identifier for the target domain.
        If omitted, auto-fetched via the API.
    :vartype zone_id: str
    """

    handler_class: AbstractDNSApi = None
    api_token: str = ""
    email: str = ""
    api_key: str = ""
    zone_id: str = ""


class CloudflareDNSApi(AbstractDNSApi):
    """Cloudflare DNS record management via the ``cloudflare`` SDK.

    :param config: Cloudflare-specific configuration.
    :type config: CloudflareDNSConfig
    """

    def __init__(self, config: CloudflareDNSConfig):
        super().__init__(config)
        self.api_token: str = config.api_token
        self.email: str = config.email
        self.api_key: str = config.api_key
        self.zone_id: str = config.zone_id
        if self.api_token:
            self.client = Cloudflare(api_token=self.api_token)
        elif self.email and self.api_key:
            self.client = Cloudflare(email=self.email, api_key=self.api_key)
        else:
            raise ValueError("Either 'api_token' or both 'email' and 'api_key' must be provided")
        if not self.zone_id:
            self.zone_id = self._fetch_zone_id()

    def _fetch_zone_id(self) -> str:
        """Auto-discover the zone ID for the configured domain.

        Queries the Cloudflare API for a zone matching ``self.domain``.

        :returns: The zone ID string.
        :rtype: str
        :raises ValueError: If no zone is found for the domain.
        """
        try:
            page = self.client.zones.list(name=self.domain)
            if page.result:
                zone = page.result[0]
                self.logger.info(f"Auto-fetched zone ID {zone.id} for {self.domain}")
                return zone.id
            raise ValueError(f"No zone found for domain '{self.domain}'")
        except cloudflare.APIStatusError as e:
            raise ValueError(
                f"Failed to fetch zone ID for {self.domain}:\n"
                f"Status Code: {e.status_code}\n"
                f"Response: {e.response}"
            ) from e

    def list_all_records(self) -> list[DNSRecord]:
        """List all DNS records for the configured domain.

        :returns: A list of ``DNSRecord`` objects.
        :rtype: list[DNSRecord]
        """
        try:
            page = self.client.dns.records.list(zone_id=self.zone_id)
            self.logger.info(f"Succeeded to list all records for {self.domain}")
            self.logger.debug(f"Got {len(page.result)} result(s)")
            records = []
            for result in page.result:
                records.append(DNSRecord(
                    domain=self.domain,
                    name=result.name.removesuffix("." + self.domain),
                    type=result.type,  # type: ignore[assignment]
                    id=result.id,
                    value=result.content or "",
                    ttl=int(result.ttl),
                    comment=result.comment or "",
                ))
            return records
        except cloudflare.APIStatusError as e:
            self.logger.warning(
                f"Failed to list records for {self.domain}:\n"
                f"Status Code: {e.status_code}\n"
                f"Response: {e.response}\n"
                f"Exception: {e}"
            )
            return []
        except Exception as e:
            self.logger.warning(
                f"Failed to list records for {self.domain}:\n"
                f"Exception: {e}"
            )
            return []

    def get_records(self, name: str, type: RECORD_TYPE) -> list[DNSRecord] | None:
        """Fetch all DNS records matching name and type from Cloudflare.

        Cloudflare allows several records to share one name and type
        (round-robin answers), so callers managing "the" record need the
        full list to detect duplicates.

        :param name: Record name (subdomain).
        :type name: str
        :param type: DNS record type.
        :type type: RECORD_TYPE
        :returns: A list of matching ``DNSRecord`` objects (empty when none
            exists), or ``None`` when the API call failed and the remote
            state is therefore unknown.
        :rtype: list[DNSRecord] | None
        """
        full_name = name + "." + self.domain
        try:
            page = self.client.dns.records.list(
                zone_id=self.zone_id,
                name={"exact": full_name},  # type: ignore[assignment]
                type=type,  # type: ignore[assignment]
            )
            self.logger.info(f"Succeeded to get {type} record(s) for {name}")
            self.logger.debug(f"Got {len(page.result)} result(s)")
            return [
                DNSRecord(
                    domain=self.domain,
                    name=name,
                    type=type,
                    id=result.id,
                    value=result.content or "",
                    ttl=int(result.ttl),
                    comment=result.comment or "",
                )
                for result in page.result
            ]
        except cloudflare.APIStatusError as e:
            self.logger.warning(
                f"Failed to fetch {type} record(s) for {name}:\n"
                f"Status Code: {e.status_code}\n"
                f"Response: {e.response}\n"
                f"Exception: {e}"
            )
            return None
        except Exception as e:
            self.logger.warning(
                f"Failed to fetch {type} record(s) for {name}:\n"
                f"Exception: {e}"
            )
            return None

    def get_record(self, name: str, type: RECORD_TYPE) -> DNSRecord | None:
        """Fetch a DNS record from Cloudflare by name and type.

        :param name: Record name (subdomain).
        :type name: str
        :param type: DNS record type.
        :type type: RECORD_TYPE
        :returns: A ``DNSRecord`` populated from the API response, or
            ``None`` if the record is not found or an error occurs.
        :rtype: DNSRecord | None
        """
        records = self.get_records(name, type)
        if records is None:
            return None
        if not records:
            self.logger.warning(f"No {type} record is found for {name}")
            return None
        return records[0]

    def set_record(self, record: DNSRecord) -> bool:
        """Create or update a DNS record on Cloudflare.

        Exactly one record is kept for the name and type: the kept record is
        updated in place (or created when none exists) and any other record
        sharing the name and type is deleted. When the current remote state
        cannot be fetched, nothing is written — creating a record on top of
        an unknown state is how duplicate records are born.

        :param record: The ``DNSRecord`` to upsert.
        :type record: DNSRecord
        :returns: ``True`` on success, ``False`` on failure.
        :rtype: bool
        """
        existing = self.get_records(record.name, record.type)
        if existing is None:
            self.logger.warning(
                f"Skipping set of {record.type} record for {record.name} as {record.value}: "
                f"remote state unknown, refusing to risk a duplicate record"
            )
            return False
        # Keep a record already carrying the desired value if there is one,
        # so a resolvable record is never needlessly replaced.
        record_to_update = next(
            (r for r in existing if r.value == record.value), existing[0] if existing else None
        )
        try:
            if record_to_update and record_to_update.id:
                self.client.dns.records.update(  # type: ignore[call-overload]
                    dns_record_id=record_to_update.id,
                    zone_id=self.zone_id,
                    name=record.name + "." + self.domain,
                    type=record.type,  # type: ignore[assignment]
                    content=record.value,
                    ttl=record.ttl,
                )
            else:
                self.client.dns.records.create(  # type: ignore[call-overload]
                    zone_id=self.zone_id,
                    name=record.name + "." + self.domain,
                    type=record.type,  # type: ignore[assignment]
                    content=record.value,
                    ttl=record.ttl,
                    proxied=False,
                )
            self.logger.info(
                f"Succeeded to set {record.type} record for {record.name} as {record.value}"
            )
        except cloudflare.APIStatusError as e:
            self.logger.warning(
                f"Failed to set {record.type} record for {record.name} as {record.value}:\n"
                f"Status Code: {e.status_code}\n"
                f"Response: {e.response}\n"
                f"Exception: {e}"
            )
            return False
        except Exception as e:
            self.logger.warning(
                f"Failed to set {record.type} record for {record.name} as {record.value}:\n"
                f"Exception: {e}"
            )
            return False

        # Collapse duplicates left over from earlier runs.
        kept_id = record_to_update.id if record_to_update else ""
        ok = True
        for extra in existing:
            if extra.id and extra.id != kept_id:
                ok = self._delete_record_by_id(extra.id, name=record.name, type=record.type) and ok
        return ok

    def _delete_record_by_id(self, record_id: str, name: str, type: RECORD_TYPE) -> bool:
        """Delete a single Cloudflare record by its record ID.

        :param record_id: The provider-specific record identifier.
        :type record_id: str
        :param name: Record name (subdomain), for logging only.
        :type name: str
        :param type: DNS record type, for logging only.
        :type type: RECORD_TYPE
        :returns: ``True`` on success, ``False`` on failure.
        :rtype: bool
        """
        try:
            self.client.dns.records.delete(
                dns_record_id=record_id,
                zone_id=self.zone_id,
            )
            self.logger.info(f"Succeeded to delete {type} record {record_id} for {name}")
            return True
        except cloudflare.APIStatusError as e:
            self.logger.warning(
                f"Failed to delete {type} record {record_id} for {name}:\n"
                f"Status Code: {e.status_code}\n"
                f"Response: {e.response}\n"
                f"Exception: {e}"
            )
            return False
        except Exception as e:
            self.logger.warning(
                f"Failed to delete {type} record {record_id} for {name}:\n"
                f"Exception: {e}"
            )
            return False

    def delete_record(self, name: str, type: RECORD_TYPE) -> bool:
        """Delete all DNS records matching name and type from Cloudflare.

        :param name: Record name (subdomain).
        :type name: str
        :param type: DNS record type.
        :type type: RECORD_TYPE
        :returns: ``True`` on success, ``False`` if no record exists or an
            error occurs.
        :rtype: bool
        """
        records_to_delete = self.get_records(name, type)
        if records_to_delete is None:
            self.logger.warning(f"Failed to delete {type} record(s) for {name}: Remote state unknown")
            return False
        if not records_to_delete:
            self.logger.warning(f"Failed to delete {type} record for {name}: Not existed")
            return False
        ok = True
        for record_to_delete in records_to_delete:
            if not record_to_delete.id:
                continue
            ok = self._delete_record_by_id(record_to_delete.id, name=name, type=type) and ok
        return ok
