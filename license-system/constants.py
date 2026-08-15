"""constants.py - plan rules mirrored from the backend so this package can
keep enforcing them offline. Keep in sync by hand with:
  - backend/services/license_service.py:PLAN_DURATIONS
  - backend/services/device_service.py:PLAN_DEVICE_LIMITS
The backend is still the authority - these are only the fallback values
used while OFFLINE_GRACE_HOURS hasn't run out yet.
"""
import os

PLAN_DEVICE_LIMITS = {"trial": 1, "monthly": 1, "yearly": 2, "lifetime": 3}

PLAN_DURATIONS_DAYS = {"trial": 7, "monthly": 30, "yearly": 365, "lifetime": None}

# How long the desktop worker/EA keeps trading on its last known-good
# license answer after losing contact with the backend. Long enough to
# survive a home internet blip mid-trade, short enough that a
# revoked/expired license can't be exploited by just unplugging the
# router.
OFFLINE_GRACE_HOURS = 48

# Local cache file location (per-OS user config dir, no extra dependency).
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".trader_gold_scalper")
CACHE_FILE = os.path.join(CACHE_DIR, "license_cache.bin")
