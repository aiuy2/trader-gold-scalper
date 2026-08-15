"""system_metrics.py - host-level metrics (CPU load, memory, disk) for the
machine running the backend/workers. Uses psutil if it's installed (not a
hard dependency - it's not in requirements.txt), otherwise falls back to
stdlib-only approximations (os.getloadavg, /proc/meminfo, shutil.disk_usage)
so this still works on a bare install.
"""
import os
import shutil
import time

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

_START_TIME = time.time()


def _memory_fallback():
    """Reads /proc/meminfo on Linux; returns None off-Linux without psutil."""
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            lines = {line.split(":")[0]: line.split(":")[1].strip() for line in f}
        total_kb = int(lines["MemTotal"].split()[0])
        available_kb = int(lines["MemAvailable"].split()[0])
        used_kb = total_kb - available_kb
        return {
            "total_mb": round(total_kb / 1024, 1),
            "used_mb": round(used_kb / 1024, 1),
            "used_pct": round(used_kb / total_kb * 100, 1) if total_kb else None,
        }
    except (FileNotFoundError, KeyError, ValueError):
        return None


def collect(app_dir=None):
    """Returns a snapshot dict of system metrics. app_dir controls which
    filesystem disk usage is reported (defaults to this repo's root)."""
    app_dir = app_dir or os.path.join(os.path.dirname(__file__), "..", "..")

    if _HAS_PSUTIL:
        vm = psutil.virtual_memory()
        memory = {
            "total_mb": round(vm.total / 1024 / 1024, 1),
            "used_mb": round(vm.used / 1024 / 1024, 1),
            "used_pct": vm.percent,
        }
        cpu_pct = psutil.cpu_percent(interval=0.1)
    else:
        memory = _memory_fallback()
        cpu_pct = None

    try:
        load1, load5, load15 = os.getloadavg()
    except (OSError, AttributeError):
        load1 = load5 = load15 = None

    disk_total, disk_used, disk_free = shutil.disk_usage(app_dir)

    return {
        "ts": time.time(),
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "cpu_percent": cpu_pct,
        "load_avg": {"1m": load1, "5m": load5, "15m": load15},
        "memory": memory,
        "disk": {
            "total_gb": round(disk_total / 1024 ** 3, 2),
            "used_gb": round(disk_used / 1024 ** 3, 2),
            "free_gb": round(disk_free / 1024 ** 3, 2),
            "used_pct": round(disk_used / disk_total * 100, 1) if disk_total else None,
        },
        "source": "psutil" if _HAS_PSUTIL else "stdlib_fallback",
    }
