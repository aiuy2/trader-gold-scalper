"""session_manager.py - tracks "last seen" per (user, device) so the
active-devices list and license device-limit checks stay accurate.
Used by middleware/authentication.py on every authenticated request that
carries an X-Device-Id header.

Keeps an in-memory cache for cheap per-request touches, and persists to
the devices table (throttled, not on every single request) so the data
survives a restart and stays visible to the admin panel / mobile app.
"""
import threading
import time
from datetime import datetime, timezone

# How often (seconds) a touch is allowed to hit the database for the same
# (user_id, device_id) pair. Every call still updates the in-memory cache.
_PERSIST_INTERVAL_SECONDS = 60

_lock = threading.Lock()
_last_seen_memory: dict[tuple[int, str], float] = {}
_last_persisted: dict[tuple[int, str], float] = {}


def touch(user_id: int, device_id: str) -> None:
    """Record that this user's device just made an authenticated request."""
    if not device_id:
        return
    key = (user_id, device_id)
    now = time.monotonic()

    with _lock:
        _last_seen_memory[key] = now
        should_persist = (now - _last_persisted.get(key, 0)) >= _PERSIST_INTERVAL_SECONDS

    if should_persist:
        _persist(user_id, device_id)
        with _lock:
            _last_persisted[key] = now


def _persist(user_id: int, device_id: str) -> None:
    # Imported lazily to avoid a hard circular-import dependency between
    # security/ (low-level) and database/ (higher-level) at module load time.
    from database.database import SessionLocal
    from database.repositories import devices as devices_repo

    db = SessionLocal()
    try:
        device = devices_repo.get_by_device_id(db, user_id, device_id)
        if device:
            devices_repo.touch(db, device)
    finally:
        db.close()


def last_seen(user_id: int, device_id: str):
    """In-memory last-seen timestamp (wall clock), or None if never touched
    this process's lifetime."""
    with _lock:
        mono = _last_seen_memory.get((user_id, device_id))
    if mono is None:
        return None
    # Approximate wall-clock time from the monotonic delta.
    delta = time.monotonic() - mono
    return datetime.now(timezone.utc).timestamp() - delta
