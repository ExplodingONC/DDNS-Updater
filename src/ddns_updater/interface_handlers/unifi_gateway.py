"""UniFi gateway IP detection via UniFi controller API.

Provides the UnifiGateway class which queries a UniFi controller
to retrieve the WAN IPv4 and IPv6 addresses of the gateway device.
"""

from __future__ import annotations

import json
import logging
import ipaddress
from typing import Optional

import requests
import urllib3

from .abstract_handler import AbstractInterfaceHandler

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UnifiGateway(AbstractInterfaceHandler):
    """Retrieves WAN IP addresses from a UniFi gateway via its controller API.

    :param controller_url: Base URL of the UniFi controller
        (e.g. ``"https://192.168.0.1"``).
    :type controller_url: str
    :param username: UniFi OS username with read-only API access.
    :type username: str
    :param password: UniFi OS password.
    :type password: str
    :param site_name: UniFi site name. Defaults to ``"default"``.
    :type site_name: str
    """

    def __init__(
        self,
        controller_url: str,
        username: str,
        password: str,
        site_name: str = "default",
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.controller_url = controller_url.rstrip("/")
        self.username = username
        self.password = password
        self.site_name = site_name

        self._api_auth_path = "/api/auth"
        self._network_api_path = f"/proxy/network/api/s/{site_name}"
        self._session = requests.Session()
        self._session.verify = False
        self._logged_in = False
        self._csrf_token: str | None = None

    def _get_auth_headers(self) -> dict[str, str]:
        """Return headers required for authenticated API requests.

        Includes the CSRF token when available, which is required by
        UniFi OS controllers for non-GET requests and sometimes for
        all requests on newer firmware versions.

        :returns: Headers dict with Content-Type and optionally X-CSRF-Token.
        :rtype: dict[str, str]
        """
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._csrf_token:
            headers["X-CSRF-Token"] = self._csrf_token
        return headers

    def _login(self) -> bool:
        """Authenticate with the UniFi controller.

        Handles UniFi OS controllers (UDM, UCG, etc.) which use
        ``/api/auth/login``. Extracts the CSRF token from the login
        response header and validates the response body for errors.

        :returns: ``True`` on success, ``False`` on failure.
        :rtype: bool
        """
        if self._logged_in:
            return True

        login_url = f"{self.controller_url}{self._api_auth_path}/login"
        payload = {"username": self.username, "password": self.password}
        headers = {"Content-Type": "application/json"}

        try:
            response = self._session.post(
                login_url, data=json.dumps(payload), headers=headers, timeout=10
            )

            # Check for explicit auth failures before raise_for_status
            if response.status_code == 403:
                try:
                    body = response.json()
                    code = body.get("code", "")
                    if code == "AUTHENTICATION_FAILED_INVALID_CREDENTIALS":
                        self.logger.warning("UniFi login failed: invalid username or password")
                        return False
                except ValueError:
                    pass
                self.logger.warning(
                    f"UniFi login rejected (HTTP 403): "
                    f"body={response.text[:500]}"
                )
                return False

            if response.status_code == 499:
                self.logger.warning(
                    "UniFi login requires 2FA. Configure the account "
                    "without two-factor authentication for API access."
                )
                return False

            response.raise_for_status()

            # Extract CSRF token from response header (UniFi OS)
            self._csrf_token = response.headers.get("X-CSRF-Token")

            # Validate response body indicates success
            try:
                body = response.json()
                # New UniFi Network 10.x returns user profile directly on success
                if "unique_id" in body or "username" in body:
                    pass  # Login succeeded
                else:
                    # Legacy format: {"meta": {"rc": "ok", ...}}
                    meta = body.get("meta", {})
                    if meta.get("rc") != "ok":
                        msg = meta.get("msg", "unknown error")
                        self.logger.warning(
                            f"UniFi login failed: {msg} "
                            f"(status={response.status_code}, body={body})"
                        )
                        return False
            except ValueError:
                # Some controller versions return empty body on success
                self.logger.debug(
                    f"UniFi login response body is not JSON: "
                    f"status={response.status_code}, "
                    f"text={response.text[:200]}"
                )

            # Verify we got a session cookie
            if not self._session.cookies.get("TOKEN"):
                self.logger.warning(
                    "UniFi login succeeded but no TOKEN cookie received. "
                    "Subsequent requests may fail."
                )

            self._logged_in = True
            if self._csrf_token:
                self.logger.debug("UniFi login successful (CSRF token acquired)")
            else:
                self.logger.debug("UniFi login successful (no CSRF token in response)")
            return True

        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"UniFi login failed: {e}")
            return False
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(
                f"Cannot reach UniFi controller at {self.controller_url}: {e}"
            )
            return False
        except requests.exceptions.Timeout:
            self.logger.warning("UniFi controller login timed out")
            return False
        except Exception as e:
            self.logger.warning(f"UniFi login error: {e}")
            return False

    def _logout(self) -> None:
        """End the session with the UniFi controller."""
        if not self._logged_in:
            return
        logout_url = f"{self.controller_url}{self._api_auth_path}/logout"
        try:
            self._session.post(
                logout_url,
                headers=self._get_auth_headers(),
                timeout=5,
            )
        except Exception:
            pass
        finally:
            self._session.close()
            self._logged_in = False
            self._csrf_token = None

    def _fetch_device_data(self) -> Optional[dict]:
        """Fetch device list from the UniFi controller.

        :returns: The parsed JSON response ``data`` list, or ``None``.
        :rtype: dict | None
        """
        if not self._logged_in:
            if not self._login():
                return None

        device_url = f"{self.controller_url}{self._network_api_path}/stat/device"

        try:
            response = self._session.get(
                device_url,
                headers=self._get_auth_headers(),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if data and "data" in data and isinstance(data["data"], list):
                return data["data"]
            return None
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"Failed to fetch UniFi device data: {e}")
            if e.response is not None and e.response.status_code == 401:
                self._logged_in = False
                self._csrf_token = None
            return None
        except Exception as e:
            self.logger.warning(f"UniFi device fetch error: {e}")
            return None

    def _find_gateway(self, devices: list[dict]) -> Optional[dict]:
        """Locate the gateway device in the device list.

        Looks for a device with ``type == "udm"`` (UniFi Dream Machine /
        Gateway family).

        :param devices: List of device dicts from the controller.
        :type devices: list[dict]
        :returns: The gateway device dict, or ``None``.
        :rtype: dict | None
        """
        for device in devices:
            if device.get("type") == "udm":
                return device
        # Log available device types for debugging
        types = [f"{d.get('name', '?')}({d.get('type', '?')})" for d in devices]
        self.logger.warning(f"UniFi gateway (type=udm) not found. Devices: {types}")
        return None

    def _get_wan_ipv4(self) -> Optional[ipaddress.IPv4Address]:
        """Retrieve the WAN IPv4 address from the gateway.

        :returns: The WAN IPv4 address, or ``None`` if unavailable.
        :rtype: ipaddress.IPv4Address | None
        """
        devices = self._fetch_device_data()
        if not devices:
            return None

        gateway = self._find_gateway(devices)
        if not gateway:
            self.logger.warning("UniFi gateway not found in device list")
            return None

        wan1 = gateway.get("wan1", {})
        ipv4 = wan1.get("ip")
        if ipv4:
            try:
                return ipaddress.IPv4Address(ipv4)
            except ValueError:
                self.logger.warning(f"Invalid IPv4 address from UniFi gateway: {ipv4}")
        return None

    def _get_wan_ipv6(self) -> Optional[ipaddress.IPv6Address]:
        """Retrieve the WAN IPv6 address from the gateway.

        Scans the ``wan1.ipv6`` list for a non-link-local address.

        :returns: The WAN IPv6 address, or ``None`` if unavailable.
        :rtype: ipaddress.IPv6Address | None
        """
        devices = self._fetch_device_data()
        if not devices:
            return None

        gateway = self._find_gateway(devices)
        if not gateway:
            self.logger.warning("UniFi gateway not found in device list")
            return None

        wan1 = gateway.get("wan1", {})
        if not wan1:
            self.logger.warning(
                f"UniFi gateway has no wan1 data. "
                f"Gateway keys: {list(gateway.keys())}"
            )
            return None
        ipv6_list = wan1.get("ipv6", [])
        if isinstance(ipv6_list, list):
            self.logger.warning(f"UniFi WAN1 IPv6 candidates: {ipv6_list}")
            for addr in ipv6_list:
                if addr.startswith("fe80:"):
                    continue
                try:
                    return ipaddress.IPv6Address(addr)
                except ValueError:
                    continue
        else:
            self.logger.warning(f"UniFi WAN1 IPv6 is not a list: {type(ipv6_list)}")
        return None

    def get_ipv4_ip(self) -> Optional[ipaddress.IPv4Address]:
        """Return the WAN IPv4 address from the UniFi gateway.

        :returns: The gateway's WAN IPv4 address, or ``None`` if
            unavailable or the controller is unreachable.
        :rtype: ipaddress.IPv4Address | None
        """
        try:
            return self._get_wan_ipv4()
        except Exception as e:
            self.logger.warning(f"Unable to get IPv4 from UniFi gateway: {e}")
            return None
        finally:
            self._logout()

    def get_ipv6_ip(self) -> Optional[ipaddress.IPv6Address]:
        """Return the WAN IPv6 address from the UniFi gateway.

        :returns: The gateway's WAN IPv6 address, or ``None`` if
            unavailable or the controller is unreachable.
        :rtype: ipaddress.IPv6Address | None
        """
        try:
            return self._get_wan_ipv6()
        except Exception as e:
            self.logger.warning(f"Unable to get IPv6 from UniFi gateway: {e}")
            return None
        finally:
            self._logout()
