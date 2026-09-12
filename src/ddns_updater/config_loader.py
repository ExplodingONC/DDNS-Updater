"""Configuration loader for DDNS task definitions.

Reads the ``ddns_config.json`` configuration file. On Linux the system
config directory ``/etc/ddns_updater/`` is checked first; if not found
the bundled sample config under ``configs/`` is used as fallback.

Cloudflare credentials are resolved in order:
1. Per-target ``credentials`` in ``ddns_config.json``
2. Environment variables ``CLOUDFLARE_API_TOKEN``, ``CLOUDFLARE_EMAIL``,
   ``CLOUDFLARE_API_KEY``, ``CLOUDFLARE_ZONE_ID``
"""

import json
import os
import pathlib
from dataclasses import dataclass
from typing import TypedDict
from .dns_api import AbstractDNSConfig, RECORD_TYPE
from .dns_api.cloudflare_api import CloudflareDNSConfig, CloudflareDNSApi

_SAMPLE_CONFIGS_DIR = pathlib.Path(__file__).parent / "configs"
"""Path to the bundled sample configuration files."""

_SYSTEM_CONFIGS_DIR = pathlib.Path("/etc/ddns_updater")
"""Path to the system-level configuration directory."""

_PROVIDER_MAP = {
    "cloudflare": (CloudflareDNSConfig, CloudflareDNSApi),
}
"""Mapping of provider names to their (config class, API class) tuples."""


@dataclass
class UniFiCredentials:
    """Credentials for accessing a UniFi controller.

    :var controller_url: Base URL of the UniFi controller.
    :vartype controller_url: str
    :var username: UniFi OS username.
    :vartype username: str
    :var password: UniFi OS password.
    :vartype password: str
    """

    controller_url: str = "https://192.168.0.1"
    username: str = ""
    password: str = ""


@dataclass
class DDNSTaskConfig:
    """Configuration for a single DNS record update task.

    :var name: The record name / subdomain (e.g. ``"www"``, ``"@"``).
    :vartype name: str
    :var type: DNS record type (e.g. ``"A"``, ``"AAAA"``).
    :vartype type: RECORD_TYPE
    :var source: IP source in ``"local"``, ``"local.<interface>"``,
        ``"unifi"``, or ``"unifi.<site_name>"`` format.
    :vartype source: str
    :var unifi_credentials: UniFi controller credentials (required
        when source starts with ``"unifi"``).
    :vartype unifi_credentials: UniFiCredentials | None
    """

    name: str = "www"
    type: RECORD_TYPE = "AAAA"
    source: str = "local"
    unifi_credentials: UniFiCredentials | None = None


class DDNSTargetConfig(TypedDict):
    """Typed dictionary for a single DNS target configuration.

    :var api: Provider-specific DNS configuration.
    :vartype api: AbstractDNSConfig
    :var task: List of record-level task configurations.
    :vartype task: list[DDNSTaskConfig]
    """

    api: AbstractDNSConfig
    task: list[DDNSTaskConfig]


def _find_config(filename: str) -> pathlib.Path:
    """Locate a configuration file.

    Checks ``/etc/ddns_updater/`` first, then falls back to the
    bundled sample configs.

    :param filename: The config file name (e.g. ``"ddns_config.json"``).
    :type filename: str
    :returns: Path to the config file.
    :rtype: pathlib.Path
    :raises FileNotFoundError: If the file is not found in either location.
    """
    system_path = _SYSTEM_CONFIGS_DIR / filename
    if system_path.is_file():
        return system_path
    bundled_path = _SAMPLE_CONFIGS_DIR / filename
    if bundled_path.is_file():
        return bundled_path
    raise FileNotFoundError(
        f"Config file '{filename}' not found in {_SYSTEM_CONFIGS_DIR} or {_SAMPLE_CONFIGS_DIR}"
    )


def _load_target_config(target: dict) -> DDNSTargetConfig:
    """Parse a single target entry from the DDNS config file.

    Resolves the provider name to the appropriate config and API
    classes, instantiates them, and pairs the DNS config with its
    list of task definitions.

    :param target: A dictionary from the ``targets`` array in
        ``ddns_config.json``.
    :type target: dict
    :returns: A dict with keys ``"api"`` (an ``AbstractDNSConfig``) and
        ``"task"`` (a list of ``DDNSTaskConfig``).
    :rtype: DDNSTargetConfig
    """
    provider = target["provider"].lower()
    config_cls, handler_cls = _PROVIDER_MAP[provider]

    credentials = target.get("credentials", {})

    if provider == "cloudflare" and not credentials:
        credentials = {}
        if token := os.environ.get("CLOUDFLARE_API_TOKEN"):
            credentials["api_token"] = token
        if email := os.environ.get("CLOUDFLARE_EMAIL"):
            credentials["email"] = email
        if api_key := os.environ.get("CLOUDFLARE_API_KEY"):
            credentials["api_key"] = api_key
        if zone_id := os.environ.get("CLOUDFLARE_ZONE_ID"):
            credentials["zone_id"] = zone_id

    dns_config = config_cls(
        handler_class=handler_cls,
        domain=target["domain"],
        timeout=target.get("timeout", 10),
        **credentials,
    )

    unifi_creds_raw = target.get("unifi_credentials")
    unifi_credentials = None
    if unifi_creds_raw:
        unifi_credentials = UniFiCredentials(
            controller_url=unifi_creds_raw.get("controller_url", "https://192.168.0.1"),
            username=unifi_creds_raw.get("username", ""),
            password=unifi_creds_raw.get("password", ""),
        )

    tasks = [
        DDNSTaskConfig(
            name=t["name"],
            type=t["type"],
            source=t.get("source", "local"),
            unifi_credentials=unifi_credentials,
        )
        for t in target.get("tasks", [])
    ]

    return {
        "api": dns_config,
        "task": tasks,
    }


def load_ddns_config(path: str | pathlib.Path | None = None) -> list[DDNSTargetConfig]:
    """Load all DDNS target configurations from a JSON file.

    :param path: Path to the JSON file. Defaults to
        ``/etc/ddns_updater/ddns_config.json`` or the bundled sample.
    :type path: str | pathlib.Path | None
    :returns: A list of dicts, each containing an ``"api"`` config and a
        ``"task"`` list for one DNS target.
    :rtype: list[DDNSTargetConfig]
    """
    if path is None:
        path = _find_config("ddns_config.json")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [_load_target_config(t) for t in data.get("targets", [])]
