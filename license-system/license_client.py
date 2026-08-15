"""license_client.py - the same two calls the web frontend makes
(frontend/js/api.js), reused here so the desktop worker/EA checks its
license against the exact same backend endpoints instead of a second,
divergent implementation:

    GET  /licenses/current           -> backend/api/licenses.py
    POST /devices                    -> backend/api/devices.py

Uses `requests` (already common, added to requirements.txt) rather than
hand-rolling urllib, since this only ever runs on a desktop machine (not
inside the FastAPI process), where an extra dependency is cheap.
"""
import requests

DEFAULT_TIMEOUT_SECONDS = 8


class LicenseClient:
    def __init__(self, api_url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    def _headers(self, access_token: str) -> dict:
        return {"Authorization": f"Bearer {access_token}"}

    def fetch_current_license(self, access_token: str) -> dict | None:
        """Mirrors GET /licenses/current. Returns None if there's no active
        license (the backend also returns null in that case)."""
        resp = requests.get(
            f"{self.api_url}/licenses/current",
            headers=self._headers(access_token),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def register_device(
        self, access_token: str, device_id: str, device_name: str = None, platform: str = None
    ) -> dict:
        """Mirrors POST /devices. Returns e.g.
        {"success": True, "device": device_id} or
        {"success": False, "error": "device_limit_reached", "limit": N}."""
        resp = requests.post(
            f"{self.api_url}/devices",
            headers=self._headers(access_token),
            json={"device_id": device_id, "device_name": device_name, "platform": platform},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()
