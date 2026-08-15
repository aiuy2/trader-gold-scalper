"""connection_alerts.py - raises alerts for MT5/broker connectivity loss
and recovery. Consumes the same shape of info trading-engine's
ConnectionState exposes (status/downtime), but stays decoupled from that
package (duck-typed dict input) so monitoring/ works standalone against
whatever reports its connection state this way - a live connector, a
worker's periodic status report, etc.
"""

_ALERT_AFTER_DOWNTIME_SECONDS = 60


def _default_notify(alert):
    print(f"[connection_alert] {alert['title']}: {alert['message']}")
    return alert


def check(connection_info, worker_id=None, notify=None,
          alert_after_seconds=_ALERT_AFTER_DOWNTIME_SECONDS):
    """connection_info: {"status": "connected"|"disconnected"|"reconnecting",
    "downtime_seconds": float, "reconnect_attempts": int}. Returns an alert
    dict if one should be raised, else None. Doesn't do de-duplication
    itself - pair with a poller that only calls this on state transitions,
    same pattern as WorkerAlertMonitor.
    """
    notify = notify or _default_notify
    status = connection_info.get("status")
    downtime = connection_info.get("downtime_seconds", 0) or 0

    if status == "disconnected" and downtime >= alert_after_seconds:
        return notify({
            "type": "connection_lost",
            "worker_id": worker_id,
            "title": "MT5 connection lost",
            "message": f"Disconnected for {int(downtime)}s "
                       f"({connection_info.get('reconnect_attempts', 0)} reconnect attempts).",
        })

    if status == "connected" and connection_info.get("just_recovered"):
        return notify({
            "type": "connection_recovered",
            "worker_id": worker_id,
            "title": "MT5 connection restored",
            "message": "Connection to MT5/broker is back.",
        })

    return None
