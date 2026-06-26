# DDNS Updater for Cloudflare / GoDaddy DNS

Monitors local IP address changes (both IPv4 and IPv6), and updates them to Cloudflare or GoDaddy DNS providers.

## Features

- Automatic IP detection via local network interface
- Cloudflare DNS via official Python SDK
- GoDaddy DNS via REST API (requires paid API access)
- SOCKS5 proxy support for GoDaddy
- Systemd journal logging on Linux
- Automatic log rotation
- Systemd service installer

## Requirements

- Python 3.12+
- Debian/Ubuntu (other distributions may require adjustments)

### System dependencies (for systemd journal support)

```bash
sudo apt-get install python3-dev libsystemd-dev
```

## Installation

### Via pipx (recommended)

```bash
pipx install --global git+https://github.com/yourusername/DDNS-Updater.git
```

### Via pip

```bash
pip install git+https://github.com/yourusername/DDNS-Updater.git
```

## Configuration

### 1. Export sample configs

```bash
sudo ddns-updater-install
```

This creates `/etc/ddns_updater/` with sample configuration files.

### 2. Edit configuration file

Edit `/etc/ddns_updater/ddns_config.json` with your DNS provider credentials and domain settings.

**Never share this file or commit it to version control!**

### Configuration format

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
      "use_proxy": false,
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

### Run directly

```bash
ddns-updater
```

### Run as systemd service

The installer sets up the service automatically:

```bash
sudo ddns-updater-install
```

Or manually:

```bash
sudo systemctl start ddns-updater
sudo systemctl enable ddns-updater  # optional, start on boot
```

### Check status

```bash
systemctl status ddns-updater
journalctl -u ddns-updater -f  # follow logs
```

## Project structure

```
ddns_updater/
├── __init__.py
├── __main__.py           # python -m ddns_updater entry point
├── ddns_updater.py       # main entry point
├── ddns_task.py          # core task logic
├── config_loader.py      # JSON config loading
├── logger.py             # logging setup
├── install.py            # systemd service installer
├── configs/              # sample configs
├── interface_handlers/   # IP detection
│   ├── abstract_handler.py
│   └── localhost.py      # local interface via psutil
└── dns_api/              # DNS provider implementations
    ├── abstract_api.py
    ├── cloudflare_api.py
    ├── godaddy_api.py
    └── utils.py
```

## License

See LICENSE file.
