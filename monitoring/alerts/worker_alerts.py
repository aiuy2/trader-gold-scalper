"""worker_alerts.py - watches worker_health verdicts over time (via
health/worker_health.py) and raises an alert only on a *transition*
(healthy -> unhealthy, or vice versa), not on every poll, so a watchdog
polling every few seconds doesn't spam the same alert forever. Also
flags crash-looping: a worker erroring repeatedly within a short window.
"""
import time

from health.worker_health import evaluate_all


def _default_notify(alert):
    print(f"[worker_alert] {alert['title']}: {alert['message']}")
    return alert


class WorkerAlertMonitor:
    def __init__(self, notify=None, crash_loop_window_seconds=300, crash_loop_threshold=3):
        self.notify = notify or _default_notify
        self.crash_loop_window_seconds = crash_loop_window_seconds
        self.crash_loop_threshold = crash_loop_threshold
        self._last_verdict = {}       # worker_id -> verdict
        self._error_timestamps = {}   # worker_id -> [ts, ts, ...]

    def poll(self, db, worker_model, min_expected_uptime_seconds=30):
        report = evaluate_all(db, worker_model, min_expected_uptime_seconds)
        alerts = []

        for w in report["workers"]:
            wid = w["worker_id"]
            previous = self._last_verdict.get(wid)
            current = w["verdict"]

            if current == "unhealthy":
                self._error_timestamps.setdefault(wid, []).append(time.time())
                self._prune_old_errors(wid)

            if previous is not None and previous != current:
                if current == "unhealthy":
                    alerts.append(self.notify({
                        "type": "worker_error", "worker_id": wid,
                        "title": "Worker went unhealthy",
                        "message": w["last_error"] or "unknown error",
                    }))
                elif previous == "unhealthy" and current == "healthy":
                    alerts.append(self.notify({
                        "type": "worker_recovered", "worker_id": wid,
                        "title": "Worker recovered",
                        "message": "Worker is healthy again.",
                    }))

            if len(self._error_timestamps.get(wid, [])) >= self.crash_loop_threshold:
                alerts.append(self.notify({
                    "type": "worker_crash_loop", "worker_id": wid,
                    "title": "Worker is crash-looping",
                    "message": f"{len(self._error_timestamps[wid])} errors in the last "
                               f"{self.crash_loop_window_seconds}s.",
                }))
                self._error_timestamps[wid] = []  # avoid re-alerting every poll

            self._last_verdict[wid] = current

        return {"report": report, "alerts": alerts}

    def _prune_old_errors(self, worker_id):
        cutoff = time.time() - self.crash_loop_window_seconds
        self._error_timestamps[worker_id] = [
            t for t in self._error_timestamps[worker_id] if t >= cutoff
        ]
