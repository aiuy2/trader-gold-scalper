"""api_health.py - checks that the backend API's own /health endpoint is
reachable, for use by an external watchdog process. Uses urllib (stdlib)
rather than `requests` since that isn't in requirements.txt.
"""
import json
import time
import urllib.error
import urllib.request


def check(base_url="http://localhost:8000", path="/health", timeout=5):
    url = base_url.rstrip("/") + path
    start = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            latency_ms = round((time.time() - start) * 1000, 2)
            body = resp.read().decode("utf-8")
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = None
            return {
                "healthy": resp.status == 200,
                "status_code": resp.status,
                "latency_ms": latency_ms,
                "body": parsed,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        return {"healthy": False, "status_code": exc.code, "latency_ms": None,
                "body": None, "error": str(exc)}
    except urllib.error.URLError as exc:
        return {"healthy": False, "status_code": None, "latency_ms": None,
                "body": None, "error": str(exc.reason)}
    except TimeoutError:
        return {"healthy": False, "status_code": None, "latency_ms": None,
                "body": None, "error": "timeout"}
