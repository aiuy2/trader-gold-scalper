"""worker_health.py - combines uptime, DB status, and MT5 health into one
overall verdict per worker, and flags workers that need attention (error
state, or "running" but suspiciously new/never actually ticked). This is
the module the alerts layer (alerts/worker_alerts.py) consumes.
"""
from metrics.worker_metrics import worker_uptime_seconds
from health.mt5_health import check_worker_record


def evaluate(worker, min_expected_uptime_seconds=30):
    mt5 = check_worker_record(worker)
    uptime = worker_uptime_seconds(worker)

    if worker.status == "error":
        verdict = "unhealthy"
    elif worker.status == "stopped":
        verdict = "stopped"
    elif worker.status == "running" and uptime < min_expected_uptime_seconds:
        verdict = "starting"
    elif worker.status == "running":
        verdict = "healthy"
    else:
        verdict = "unknown"

    return {
        "worker_id": worker.id,
        "verdict": verdict,
        "status": worker.status,
        "uptime_seconds": round(uptime, 1),
        "mt5": mt5,
        "last_error": worker.last_error,
    }


def evaluate_all(db, worker_model, min_expected_uptime_seconds=30):
    workers = db.query(worker_model).all()
    reports = [evaluate(w, min_expected_uptime_seconds) for w in workers]
    needs_attention = [r for r in reports if r["verdict"] == "unhealthy"]
    return {"workers": reports, "needs_attention": needs_attention}
