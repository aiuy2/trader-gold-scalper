"""device_binding.py - standalone, non-backend version of the device-limit
rule in backend/services/device_service.py. This is the file
license_service.py's docstring points to: the desktop worker/EA calls
LicenseGuard.enforce() once before it starts trading (and can call it
again periodically) instead of trusting a license forever after the
first check.

Enforcement order on every call:
  1. Ask the backend (GET /licenses/current + POST /devices) - it is
     always the authority when reachable.
  2. If the backend says no (invalid license, device limit reached,
     expired), that's final - raise, never fall back to the cache to
     talk yourself into a "yes".
  3. If the backend is unreachable (offline, DNS down, etc.), fall back
     to the last cached answer for OFFLINE_GRACE_HOURS - and still check
     that cached answer's own expiry.
"""
import hashlib
import platform
import uuid
from datetime import datetime, timezone

import requests

import cache
from constants import OFFLINE_GRACE_HOURS
from exceptions import DeviceLimitReached, LicenseExpired, LicenseInvalid, OfflineGraceExpired
from license_client import LicenseClient


def get_device_id() -> str:
    """Stable per-machine fingerprint (MAC-derived NIC id + hostname +
    OS), hashed so nothing identifying is stored/sent in the clear.
    Deterministic across runs on the same machine; different on another
    one - which is the whole point of a device limit."""
    raw = f"{uuid.getnode()}:{platform.node()}:{platform.system()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _check_expiry(license_data: dict) -> None:
    if not license_data.get("is_active", True):
        raise LicenseInvalid("license is not active")
    expires_at = license_data.get("expires_at")
    if not expires_at:
        return  # lifetime plan
    expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    if datetime.now(timezone.utc) >= expires_dt:
        raise LicenseExpired(f"license expired at {expires_at}")


class LicenseGuard:
    def __init__(self, api_url: str, device_id: str = None):
        self.client = LicenseClient(api_url)
        self.device_id = device_id or get_device_id()

    def enforce(self, access_token: str, device_name: str = None, platform_name: str = None) -> dict:
        """Returns the license dict (same shape as GET /licenses/current)
        on success. Raises an exceptions.LicenseError subclass otherwise -
        callers must treat any of those as "do not trade"."""
        try:
            license_data = self.client.fetch_current_license(access_token)
            device_result = self.client.register_device(
                access_token, self.device_id, device_name, platform_name
            )
        except requests.exceptions.HTTPError as exc:
            # Backend is reachable and gave a definitive no (e.g. expired/
            # revoked auth token) - never soften that with the cache.
            raise LicenseInvalid(f"backend rejected the request: {exc}") from exc
        except requests.exceptions.RequestException:
            return self._enforce_from_cache()

        if not device_result.get("success", True):
            if device_result.get("error") == "device_limit_reached":
                raise DeviceLimitReached(device_result.get("limit"))
            raise LicenseInvalid(device_result.get("error", "device registration failed"))

        if license_data is None:
            raise LicenseInvalid("no active license on this account")

        _check_expiry(license_data)
        cache.save(license_data, self.device_id)
        return license_data

    def _enforce_from_cache(self) -> dict:
        cached = cache.load(self.device_id)
        if cached is None:
            raise OfflineGraceExpired(
                "backend unreachable and there is no local license cache for this device"
            )

        cached_at = datetime.fromisoformat(cached["cached_at"])
        age_hours = (datetime.now(timezone.utc) - cached_at).total_seconds() / 3600
        if age_hours > OFFLINE_GRACE_HOURS:
            raise OfflineGraceExpired(
                f"backend unreachable and the cached license is {age_hours:.1f}h old "
                f"(offline grace period is {OFFLINE_GRACE_HOURS}h)"
            )

        license_data = cached["license"]
        _check_expiry(license_data)  # a cached license can still expire while offline
        return license_data
