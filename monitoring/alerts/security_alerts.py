"""security_alerts.py - scans security-log entries (the JSON-lines format
written by trading-engine's bot_logging/security_logger.py: {"ts", "event",
...}) for patterns worth alerting a human about: repeated license
rejections (possible key-sharing/brute-force), and any emergency stop
(always alerted, never suppressed).
"""
import json
import time


def _default_notify(alert):
    print(f"[security_alert] {alert['title']}: {alert['message']}")
    return alert


def load_entries(log_path, since_ts=None):
    entries = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if since_ts is None or entry.get("ts", 0) >= since_ts:
                    entries.append(entry)
    except FileNotFoundError:
        pass
    return entries


def scan(entries, notify=None, rejection_threshold=5, rejection_window_seconds=600):
    """entries: list of parsed security-log dicts, oldest first. Returns
    the list of raised alerts."""
    notify = notify or _default_notify
    alerts = []

    for entry in entries:
        if entry.get("event") == "emergency_stop_triggered":
            alerts.append(notify({
                "type": "emergency_stop",
                "title": "Emergency stop triggered",
                "message": entry.get("reason", "no reason given"),
            }))

    rejections = [e for e in entries if e.get("event") == "license_rejected"]
    if rejections:
        window_start = rejections[-1]["ts"] - rejection_window_seconds
        recent = [e for e in rejections if e["ts"] >= window_start]
        if len(recent) >= rejection_threshold:
            alerts.append(notify({
                "type": "repeated_license_rejections",
                "title": "Repeated license rejections",
                "message": f"{len(recent)} rejections in the last "
                           f"{rejection_window_seconds // 60} minutes.",
            }))

    return alerts


def scan_log_file(log_path, since_ts=None, **kwargs):
    return scan(load_entries(log_path, since_ts=since_ts), **kwargs)
