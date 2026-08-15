"""exceptions.py - errors device_binding.LicenseGuard.enforce() can raise.
The desktop worker/EA should catch LicenseError (the common base) and
refuse to start/continue trading - never trade with an unenforced
license.
"""


class LicenseError(Exception):
    """Base class - catch this to cover every reason enforcement failed."""


class LicenseInvalid(LicenseError):
    """No active license for this account, or the server rejected it."""


class LicenseExpired(LicenseError):
    """The license's expires_at has passed."""


class DeviceLimitReached(LicenseError):
    """This device isn't already bound and the plan's device limit is full."""

    def __init__(self, limit: int):
        self.limit = limit
        super().__init__(f"device limit reached ({limit} device(s) allowed on this plan)")


class OfflineGraceExpired(LicenseError):
    """Backend was unreachable and either there's no cached license, or the
    cached one is older than constants.OFFLINE_GRACE_HOURS."""
