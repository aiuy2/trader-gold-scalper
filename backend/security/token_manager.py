"""token_manager.py - refresh tokens + access-token revocation.

app/security.py issues short-lived JWT access tokens (JWT_EXPIRE_MINUTES,
default 60) but has no way to get a new one without logging in again, and
no way to invalidate a token early (logout, revoked license, stolen
device). This module adds both:

  - long-lived opaque refresh tokens, stored server-side (hash only) so
    they can be looked up, rotated, and revoked.
  - a denylist of access tokens invalidated before their natural expiry
    (used at logout / device revoke), checked by app/dependencies.py.

In-memory store: fine for a single backend process / dev+small-scale
deployment. Swap _refresh_tokens / _denylist for a Redis-backed store
before running more than one backend process, since state wouldn't be
shared across them.
"""
import hashlib
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

REFRESH_TOKEN_TTL_DAYS = 30

_lock = threading.Lock()
# token_hash -> {"user_id", "email", "device_id", "expires_at"}
_refresh_tokens: dict[str, dict] = {}
# jti -> expiry (epoch seconds) for revoked access tokens, purged lazily
_denylist: dict[str, float] = {}


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_refresh_token(user_id: int, email: str, device_id: str = None) -> str:
    """Creates a new opaque refresh token and stores its hash. Returns the
    raw token - give this to the client, never persist it in plaintext."""
    raw_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
    with _lock:
        _refresh_tokens[_hash(raw_token)] = {
            "user_id": user_id,
            "email": email,
            "device_id": device_id,
            "expires_at": expires_at,
        }
    return raw_token


def redeem_refresh_token(raw_token: str):
    """Validates a refresh token and rotates it (old one invalidated, a new
    one issued) - standard rotation so a leaked token can only be replayed
    once before the mismatch is detectable.
    Returns {"user_id", "email", "new_refresh_token"} or None if invalid/expired."""
    token_hash = _hash(raw_token)
    with _lock:
        entry = _refresh_tokens.pop(token_hash, None)

    if entry is None:
        return None
    if entry["expires_at"] < datetime.now(timezone.utc):
        return None

    new_token = issue_refresh_token(entry["user_id"], entry["email"], entry["device_id"])
    return {
        "user_id": entry["user_id"],
        "email": entry["email"],
        "new_refresh_token": new_token,
    }


def revoke_refresh_token(raw_token: str) -> bool:
    with _lock:
        return _refresh_tokens.pop(_hash(raw_token), None) is not None


def revoke_all_for_user(user_id: int) -> int:
    """Used on password change / license revocation / 'log out everywhere'."""
    with _lock:
        to_remove = [h for h, e in _refresh_tokens.items() if e["user_id"] == user_id]
        for h in to_remove:
            del _refresh_tokens[h]
    return len(to_remove)


def denylist_access_token(jti: str, expires_at: datetime) -> None:
    """Marks an access token's jti as revoked until its natural expiry."""
    with _lock:
        _denylist[jti] = expires_at.timestamp()


def is_denylisted(jti: str) -> bool:
    if not jti:
        return False
    now = time.time()
    with _lock:
        expiry = _denylist.get(jti)
        if expiry is None:
            return False
        if expiry < now:
            del _denylist[jti]
            return False
        return True
