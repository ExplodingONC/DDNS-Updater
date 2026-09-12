# DDNS Updater for Cloudflare

Monitors local IP address changes (both IPv4 and IPv6), and updates them to Cloudflare DNS.

## Features

- Automatic IP detection via local network interface
- Cloudflare DNS via official Python SDK
- Docker support

## Requirements

- Python 3.14+

## Installation

```bash
docker compose up -d
```

## Configuration

### 1. Create configuration file

Copy the sample configuration and edit it with your Cloudflare credentials:

```bash
cp src/ddns_updater/configs/ddns_config.sample.json ddns_config.json
```

### 2. Configuration format

**Never share this file or commit it to version control!**

#### Cloudflare authentication

Cloudflare supports three credential types. `zone_id` is optional and auto-fetched if omitted.

**User API Token** (`cfut_`) or **Account API Token** (`cfat_`):

```json
{
  "provider": "cloudflare",
  "domain": "example.com",
  "credentials": {
    "api_token": "cfut_xxx or cfat_xxx"
  },
  "tasks": [...]
}
```

**Global API Key** (`cfk_`):

```json
{
  "provider": "cloudflare",
  "domain": "example.com",
  "credentials": {
    "email": "you@example.com",
    "api_key": "cfk_xxx"
  },
  "tasks": [...]
}
```

#### Full example

```json
{
  "targets": [
    {
      "provider": "cloudflare",
      "domain": "example.com",
      "timeout": 10,
      "credentials": {
        "api_token": "cfut_xxx"
      },
      "tasks": [
        {
          "name": "www",
          "type": "AAAA",
          "source": "local.eno4"
        },
        {
          "name": "@",
          "type": "A",
          "source": "local.enp1s0"
        }
      ]
    }
  ]
}
```

### Source formats

- `"local.<interface>"` - Read IP from a specific network interface (e.g., `"local.eno4"`)
- `"local"` - Auto-detect network interface

## Usage

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DDNS_LOG_DIR` | `/var/log/ddns_updater` (Linux) | Directory for log files. Set to `/dev/null` to disable. |
| `DDNS_LOG_LEVEL` | `INFO` | Minimum log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

## Project structure

```
ddns_updater/
├── __init__.py
├── ddns_updater.py       # main entry point
├── ddns_task.py          # core task logic
├── config_loader.py      # JSON config loading
├── logger.py             # logging setup
├── configs/              # sample configs
├── interface_handlers/   # IP detection
│   ├── abstract_handler.py
│   └── localhost.py      # local interface via psutil
└── dns_api/              # DNS provider implementations
    ├── abstract_api.py
    ├── cloudflare_api.py
    └── utils.py
```

## License

See LICENSE file.
