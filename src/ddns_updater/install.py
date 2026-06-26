"""Systemd service installer and config exporter for Linux.

Registers the ``ddns-updater`` entry point as a systemd service
and exports sample configuration files to ``~/.ddns_updater/``.

This module is Linux-only and raises ``RuntimeError`` on other platforms.
Requires root privileges for systemd operations.

Prerequisite: Install with ``pipx install --global ddns-updater`` so the
executable is available system-wide (typically in ``/usr/local/bin/``).
"""

import platform
import shutil
import pathlib
import subprocess

from .config_loader import _SAMPLE_CONFIGS_DIR, _SYSTEM_CONFIGS_DIR

_SERVICE_NAME = "ddns-updater.service"


def _check_platform() -> None:
    """Raise an error if not running on Linux."""
    if platform.system() != "Linux":
        raise RuntimeError("ddns-updater-install is only supported on Linux")


def _export_configs() -> None:
    """Copy sample configuration files to the system config directory."""

    try:
        _SYSTEM_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise PermissionError(
            f"Permission denied: cannot create {_SYSTEM_CONFIGS_DIR}. "
            f"Run with sudo."
        )

    for sample_file in _SAMPLE_CONFIGS_DIR.glob("*.sample.json"):
        target = _SYSTEM_CONFIGS_DIR / sample_file.name.removesuffix(".sample")
        if target.exists():
            print(f"  [skip] {target} already exists")
        else:
            try:
                shutil.copy2(sample_file, target)
                print(f"  [created] {target}")
            except PermissionError:
                raise PermissionError(
                    f"Permission denied: cannot write {target}. "
                    f"Run with sudo."
                )


def _create_service_file() -> pathlib.Path:
    """Write the systemd service file and return its path."""

    executable = shutil.which("ddns-updater")
    if executable is None:
        raise FileNotFoundError(
            "ddns-updater command not found. "
            "Install with: pipx install --global ddns-updater"
        )

    service_content = f"""\
[Unit]
Description=DDNS Updater
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={executable}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    systemd_dir = pathlib.Path("/etc/systemd/system")
    try:
        systemd_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise PermissionError(
            f"Permission denied: cannot create {systemd_dir}. "
            f"Run with sudo."
        )
    service_path = systemd_dir / _SERVICE_NAME
    try:
        service_path.write_text(service_content, encoding="utf-8")
    except PermissionError:
        raise PermissionError(
            f"Permission denied: cannot write {service_path}. "
            f"Run with sudo."
        )
    print(f"  [created] {service_path}")
    return service_path


def _enable_service() -> None:
    """Reload systemd daemon and enable/start the service."""

    for cmd in [
        ["systemctl", "daemon-reload"],
        ["systemctl", "enable", _SERVICE_NAME],
        ["systemctl", "start", _SERVICE_NAME],
    ]:
        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            raise RuntimeError("systemctl not found. Is this a systemd-based system?")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Command failed: {' '.join(cmd)}\n"
                f"Error: {e}\n"
                f"Try running with sudo."
            )
    print(f"  [enabled] {_SERVICE_NAME}")


def main() -> None:
    """Install ddns-updater as a systemd service.

    Exports sample configs to ``/etc/ddns_updater/``, creates the service
    file, and enables it. Requires root privileges.
    """

    _check_platform()

    print("Exporting sample configurations...")
    _export_configs()

    print("Creating systemd service file...")
    _create_service_file()

    print("Enabling and starting service...")
    _enable_service()

    print("\nDone. Use 'systemctl status ddns-updater' to check status.")


if __name__ == "__main__":
    main()
