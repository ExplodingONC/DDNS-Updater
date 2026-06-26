# DDNS-Updater

Dynamic DNS updater that monitors local IP changes and syncs them to Cloudflare or GoDaddy DNS providers.

## Project Structure

```
DDNS-Updater/
├── src/ddns_updater/
│   ├── ddns_updater.py      # Entry point - thread pool launcher
│   ├── ddns_task.py          # Core task logic - IP detection & DNS sync loop
│   ├── logger.py             # TaskLogger - file, stdout, systemd journal logging
│   ├── config_loader.py      # Loads 3 config JSON files, builds config objects
│   ├── configs/
│   │   ├── ddns_config.sample.json  # DNS providers & task targets (copy to ddns_config.json)
│   │   └── router_config.sample.json # Router SSH credentials (copy to router_config.json)
│   ├── dns_api/
│   │   ├── abstract_api.py   # AbstractDNSApi/AbstractDNSConfig base classes
│   │   ├── cloudflare_api.py # Cloudflare DNS implementation
│   │   ├── godaddy_api.py    # GoDaddy DNS implementation
│   │   └── utils.py          # DNSRecord, ProxyHelper, RECORD_TYPE
│   └── local_utils/
│       ├── localhost.py       # Local IP detection via psutil
│       └── asus_router.py    # ASUS router WAN IP via SSH (paramiko)
├── logs/                     # Runtime log files
└── pyproject.toml            # Poetry config
```

## Design Overview

- **Entry point**: `ddns_updater.py` spawns one thread per domain config via `ThreadPool`.
- **Task loop**: Each `DDNSTask` runs an infinite loop, checking IPs every 60-120s (randomized).
- **IP sources**: `"local.<interface>"` (via psutil on specified interface, e.g. `"local.eno4"`) or `"router"` (via SSH to ASUS router). Interface is optional; omit for auto-detection.
- **DNS providers**: Abstract `AbstractDNSApi` with Cloudflare and GoDaddy implementations. Each provider has its own config dataclass extending `AbstractDNSConfig`.
- **Update logic**: Compares local IP to remote DNS record. Pushes update if different. Removes record if NAT/private IP detected (router mode).
- **Proxy support**: SOCKS5 proxy via environment variable for GoDaddy API.
- **Logging**: `TaskLogger` writes to stdout, log files (rotated daily), and systemd journal.
- **Config**: Two JSON files under `configs/`, all gitignored (samples are not):
  - `configs/ddns_config.json` — DNS providers, domains, and task definitions
  - `configs/router_config.json` — ASUS router SSH credentials

## Key Conventions

- Python 3.14+, dataclasses for configs/models
- Absolute imports using `src.ddns_updater.*` prefix
- `RECORD_TYPE = Literal["A", "AAAA", "CNAME", "MX", "NS", "SOA", "SRV", "TXT"]`
- Credentials in `configs/*.json` (all gitignored; `.sample.json` files are tracked)
- Run as systemd service on Debian/Ubuntu

## Adding a New DNS Provider

1. Create a new file in `dns_api/` (e.g., `newprovider_api.py`)
2. Define a config dataclass extending `AbstractDNSConfig`
3. Implement `AbstractDNSApi` with `get_record`, `set_record`, `delete_record`
4. Export from `dns_api/__init__.py`
