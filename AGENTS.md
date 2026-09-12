# DDNS-Updater

Dynamic DNS updater that monitors local IP changes and syncs them to Cloudflare DNS.

## Project Structure

```
DDNS-Updater/
├── src/ddns_updater/
│   ├── ddns_updater.py      # Entry point - thread pool launcher
│   ├── ddns_task.py          # Core task logic - IP detection & DNS sync loop
│   ├── logger.py             # TaskLogger - stdout & file logging
│   ├── config_loader.py      # Loads config JSON, builds config objects
│   ├── configs/
│   │   └── ddns_config.sample.json  # Cloudflare credentials & task targets (copy to ddns_config.json)
│   ├── dns_api/
│   │   ├── abstract_api.py   # AbstractDNSApi/AbstractDNSConfig base classes
│   │   ├── cloudflare_api.py # Cloudflare DNS implementation
│   │   └── utils.py          # DNSRecord, RECORD_TYPE
│   └── interface_handlers/
│       ├── abstract_handler.py
│       └── localhost.py       # Local IP detection via psutil
├── pyproject.toml            # PEP 621 config (hatchling build)
├── Dockerfile                # Multi-stage Docker build
├── docker-compose.yml        # Docker Compose config
└── .dockerignore
```

## Design Overview

- **Entry point**: `ddns_updater.py` spawns one thread per domain config via `ThreadPool`.
- **Task loop**: Each `DDNSTask` runs an infinite loop, checking IPs every 60 seconds.
- **IP sources**: `"local.<interface>"` (via psutil on specified interface, e.g. `"local.eno4"`) or `"local"` (auto-detect).
- **DNS providers**: Abstract `AbstractDNSApi` with Cloudflare implementation.
- **Update logic**: Compares local IP to remote DNS record. Pushes update if different.
- **Logging**: `TaskLogger` writes to stdout and optionally to log files.
- **Config**: `ddns_config.json` mounted via Docker volume (gitignored; sample is tracked).

## Key Conventions

- Python 3.14+, dataclasses for configs/models
- Absolute imports using `src.ddns_updater.*` prefix
- `RECORD_TYPE = Literal["A", "AAAA", "CNAME", "MX", "NS", "SOA", "SRV", "TXT"]`
- Credentials in `configs/*.json` (all gitignored; `.sample.json` files are tracked)
- Docker-only deployment

## Build System

- **Package manager**: uv (migrated from Poetry)
- **Build backend**: hatchling
- **Python**: >=3.14
- **Dependencies**: psutil, cloudflare, requests

### Common commands

```bash
# Install dependencies
uv sync

# Run directly
uv run ddns-updater

# Build package
uv build

# Install locally
uv tool install --system .
```

## Docker

```bash
# Build image (from source repo)
docker build -t ddns-updater .
```

## Adding a New DNS Provider

1. Create a new file in `dns_api/` (e.g., `newprovider_api.py`)
2. Define a config dataclass extending `AbstractDNSConfig`
3. Implement `AbstractDNSApi` with `get_record`, `set_record`, `delete_record`
4. Export from `dns_api/__init__.py`
5. Register in `_PROVIDER_MAP` in `config_loader.py`
