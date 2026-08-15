"""mt5_health.py - MT5 connectivity health, in two modes:

  - check_connector(connector): direct check when running in the same
    process as a live trading-engine connector (duck-typed: just needs
    get_account_info()). Mirrors trading-engine/protection/mt5_monitor.py
    but standalone, since monitoring/ shouldn't require importing the
    trading-engine package to function.
  - check_worker_record(worker): indirect check from the monitoring
    service's own process, which normally only sees the trading_workers
    DB row (no direct handle to another process's connector) - infers
    health from status + last_error text.
"""
import time

_MT5_ERROR_HINTS = ("mt5", "connect", "terminal", "login", "broker")


def check_connector(connector, timeout_ok=True):
    """Best-effort live check. Returns {"healthy", "detail"}."""
    try:
        info = connector.get_account_info()
        if info is None:
            return {"healthy": False, "detail": "account_info_unavailable"}
        return {"healthy": True, "detail": "ok", "checked_at": time.time()}
    except Exception as exc:  # noqa: BLE001 - any failure means unhealthy
        return {"healthy": False, "detail": str(exc)}


def check_worker_record(worker):
    """Infers MT5 health from the DB row alone (status + last_error)."""
    if worker.status == "running":
        return {"healthy": True, "detail": "worker_running"}

    if worker.status == "error":
        error_text = (worker.last_error or "").lower()
        looks_mt5_related = any(hint in error_text for hint in _MT5_ERROR_HINTS)
        return {
            "healthy": False,
            "detail": worker.last_error or "worker_in_error_state",
            "likely_mt5_related": looks_mt5_related,
        }

    return {"healthy": None, "detail": f"worker_status_{worker.status}"}
