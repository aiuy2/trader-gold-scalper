# license-system/

Standalone device-binding + license enforcement for anything that runs
**outside** the FastAPI process - i.e. a desktop worker/EA wrapping
`trading-platform/trading-engine`. The backend
(`backend/services/license_service.py`, `backend/services/device_service.py`)
is always the source of truth; this package just calls it the same way
`frontend/` does, and keeps enforcing the last answer for a short grace
period if the machine loses internet mid-session (see
`constants.OFFLINE_GRACE_HOURS`).

It is deliberately **not** a Python package you `pip install` or `import
license-system` (hyphens aren't valid in an import name). Add this folder
itself to `sys.path`, the same way `backend/services/bot_service.py` and
`backtest/engine/backtest_engine.py` add `trading-platform/trading-engine`
to theirs, then import the flat modules directly:

```python
import os
import sys

LICENSE_SYSTEM_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "license-system"))
if LICENSE_SYSTEM_PATH not in sys.path:
    sys.path.insert(0, LICENSE_SYSTEM_PATH)

from device_binding import LicenseGuard
from exceptions import LicenseError

guard = LicenseGuard(api_url="https://api.example.com")

try:
    license = guard.enforce(access_token, device_name="DESKTOP-1", platform_name="windows")
except LicenseError as exc:
    print(f"refusing to trade: {exc}")
    raise SystemExit(1)

# license is a dict shaped like GET /licenses/current's response.
# Call guard.enforce(...) again periodically (e.g. once per hour) from
# the worker's own loop - it is not wired into main/engine.py itself so
# a license check never blocks/slows down every price tick.
```

`access_token` is the same JWT the desktop app got from `POST /auth/login`
(see `backend/api/auth.py`) - this package doesn't handle login itself,
only what happens after.

## Files
- `device_binding.py` - `LicenseGuard`, the entry point above, and
  `get_device_id()` (stable per-machine fingerprint).
- `license_client.py` - the two HTTP calls (`GET /licenses/current`,
  `POST /devices`), same endpoints the web frontend uses.
- `cache.py` - encrypted last-known-good answer, used only when the
  backend is unreachable.
- `constants.py` - plan device limits / durations mirrored from the
  backend, plus `OFFLINE_GRACE_HOURS`.
- `exceptions.py` - `LicenseError` and its subclasses; catch the base
  class to cover every reason enforcement failed.

## Limitations
Local caching + a device fingerprint raises the bar, it doesn't make
offline enforcement airtight - a determined user with full access to
their own machine can still tamper with it (e.g. rolling the system
clock back). The backend call is what actually matters; the cache exists
so a Wi-Fi blip doesn't kill a live trade, not to replace server-side
enforcement.
