"""mt5_monitor.py - lightweight connectivity check the engine runs before
trusting a connector each loop iteration. Mirrored (standalone, no import
of this package) by monitoring/health/mt5_health.py:check_connector, which
the backend's monitoring service uses instead when it can't hold a direct
handle to another process's connector.
"""
import time


def is_connector_healthy(connector) -> bool:
    try:
        info = connector.get_account_info()
        return info is not None
    except Exception:  # noqa: BLE001 - any failure means unhealthy
        return False


def wait_for_reconnect(connector, max_attempts: int = 5, delay_seconds: float = 3.0) -> bool:
    """Polls the connector until it's healthy again or attempts run out.
    Used if a live MT5 terminal briefly drops connection mid-session."""
    for attempt in range(max_attempts):
        if is_connector_healthy(connector):
            return True
        time.sleep(delay_seconds)
    return False
