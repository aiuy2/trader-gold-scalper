"""cache.py - the last known-good license answer, stored locally so
device_binding.LicenseGuard can keep enforcing it for a bounded grace
period if the backend becomes unreachable mid-session (see
constants.OFFLINE_GRACE_HOURS).

Encrypted at rest with Fernet (same approach as backend/security/
encryption.py) using a key derived from the device's own fingerprint, so
the cache file is useless if copied to a different machine - it won't
decrypt there. This is a courtesy against casual tampering (e.g. editing
expires_at in a plaintext file), not a defense against a determined
attacker with full access to the machine; the backend call remains the
real authority whenever it's reachable.
"""
import base64
import hashlib
import json
import os
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken

from constants import CACHE_DIR, CACHE_FILE


def _fernet_for_device(device_id: str) -> Fernet:
    digest = hashlib.sha256(f"license-cache:{device_id}".encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def save(license_data: dict, device_id: str) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    payload = {
        "license": license_data,
        "device_id": device_id,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    token = _fernet_for_device(device_id).encrypt(json.dumps(payload).encode("utf-8"))
    with open(CACHE_FILE, "wb") as fh:
        fh.write(token)
    try:
        os.chmod(CACHE_FILE, 0o600)
    except OSError:
        pass  # best-effort on platforms without POSIX permissions (Windows)


def load(device_id: str) -> dict | None:
    """Returns {"license": ..., "device_id": ..., "cached_at": iso-str} or
    None if there's no cache, it's unreadable, or it belongs to a
    different device_id (e.g. copied from another machine)."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "rb") as fh:
            token = fh.read()
        payload = json.loads(_fernet_for_device(device_id).decrypt(token).decode("utf-8"))
    except (InvalidToken, ValueError, json.JSONDecodeError, OSError):
        return None
    if payload.get("device_id") != device_id:
        return None
    return payload


def clear() -> None:
    try:
        os.remove(CACHE_FILE)
    except FileNotFoundError:
        pass
