"""worker_metrics.py - aggregates trading_workers table rows into fleet-wide
metrics (how many running/stopped/error, per-worker uptime). Takes a
SQLAlchemy session as a parameter rather than importing SessionLocal
directly, so this module has no hard dependency on how the caller wires
up the database.
"""
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


def count_by_status(db, worker_model):
    """worker_model: the TradingWorker model class (passed in to avoid
    monitoring/ importing backend/'s package layout directly)."""
    counts = {"running": 0, "stopped": 0, "error": 0}
    rows = db.query(worker_model.status).all()
    for (status,) in rows:
        counts[status] = counts.get(status, 0) + 1
    return counts


def worker_uptime_seconds(worker):
    if worker.status != "running" or worker.started_at is None:
        return 0.0
    started = worker.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return (_now() - started).total_seconds()


def collect(db, worker_model):
    """Returns {"counts": {...}, "workers": [{"id", "status", "symbol",
    "mode", "uptime_seconds", "last_error"}, ...]}"""
    workers = db.query(worker_model).all()
    return {
        "counts": count_by_status(db, worker_model),
        "workers": [
            {
                "id": w.id,
                "user_id": w.user_id,
                "symbol": w.symbol,
                "status": w.status,
                "mode": w.mode,
                "uptime_seconds": round(worker_uptime_seconds(w), 1),
                "last_error": w.last_error,
            }
            for w in workers
        ],
    }
