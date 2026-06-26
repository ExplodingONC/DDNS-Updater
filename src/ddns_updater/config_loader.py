"""Configuration loader for DDNS task definitions.

Reads the ``ddns_config.json`` configuration file. On Linux the system
config directory ``/etc/ddns_updater/`` is checked first; if not found
the bundled sample config under ``configs/`` is used as fallback.
"""

import json
import pathlib
from dataclasses import dataclass
from typing import TypedDict
from .dns_api import AbstractDNSConfig, RECORD_TYPE
from .dns_api.cloudflare_api import CloudflareDNSConfig, CloudflareDNSApi
from .dns_api.godaddy_api import GodaddyDNSConfig, GodaddyDNSApi

_SAMPLE_CONFIGS_DIR = pathlib.Path(__file__).parent / "configs"
"""Path to the bundled sample configuration files."""

_SYSTEM_CONFIGS_DIR = pathlib.Path("/etc/ddns_updater")
"""Path to the system-level configuration directory."""

_PROVIDER_MAP = {
    "cloudflare": (CloudflareDNSConfig, CloudflareDNSApi),
    "godaddy": (GodaddyDNSConfig, GodaddyDNSApi),
}
"""Mapping of provider names to their (config class, API class) tuples."""


@dataclass
class DDNSTaskConfig:
    """Configuration for a single DNS record update task.

    :var name: The record name / subdomain (e.g. ``"www"``, ``"@"``).
    :vartype name: str
    :var type: DNS record type (e.g. ``"A"``, ``"AAAA"``).
    :vartype type: RECORD_TYPE
    :var source: IP source in ``"local"`` or ``"local.<interface>"`` format.
    :vartype source: str
    """

    name: str = "www"
    type: RECORD_TYPE = "AAAA"
    source: str = "local"


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

    dns_config = config_cls(
        handler_class=handler_cls,
        use_proxy=target.get("use_proxy", False),
        domain=target["domain"],
        timeout=target.get("timeout", 10),
        **target.get("credentials", {}),
    )

    tasks = [
        DDNSTaskConfig(
            name=t["name"],
            type=t["type"],
            source=t.get("source", "local"),
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
