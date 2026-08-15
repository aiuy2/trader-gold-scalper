"""database_health.py - checks that the database is actually reachable and
responsive (not just that SQLAlchemy could build an Engine object), by
running a trivial SELECT 1 and timing it.
"""
import time

from sqlalchemy import text


def check(engine, timeout_warn_ms=200):
    """engine: a SQLAlchemy Engine (backend.database.database.engine).
    Returns {"healthy": bool, "latency_ms": float|None, "error": str|None}."""
    start = time.time()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.time() - start) * 1000, 2)
        return {
            "healthy": True,
            "latency_ms": latency_ms,
            "slow": latency_ms > timeout_warn_ms,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - any DB failure means unhealthy
        return {
            "healthy": False,
            "latency_ms": None,
            "slow": False,
            "error": str(exc),
        }
