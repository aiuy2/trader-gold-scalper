"""license_service.py - issues a trial license on signup, activates a
purchased license key, and reports current license status. Wraps
database/repositories/licenses.py; the standalone license-system/ package
enforces the same rules offline (e.g. inside the desktop worker/EA)."""
import secrets
from datetime import datetime, timedelta, timezone

from database.database import SessionLocal
from database.repositories import licenses as licenses_repo

PLAN_DURATIONS = {
    "trial": timedelta(days=7),
    "monthly": timedelta(days=30),
    "yearly": timedelta(days=365),
    "lifetime": None,
}


def _generate_key() -> str:
    return "-".join(secrets.token_hex(4).upper() for _ in range(4))


def _public(lic) -> dict:
    return {
        "license_key": lic.license_key, "plan": lic.plan,
        "is_active": lic.is_active, "expires_at": lic.expires_at,
    }


class LicenseService:
    @staticmethod
    def issue_trial(user_id: int):
        db = SessionLocal()
        try:
            existing = licenses_repo.get_active_for_user(db, user_id)
            if existing:
                return existing
            lic = licenses_repo.create(db, user_id, license_key=_generate_key(), plan="trial")
            lic.expires_at = datetime.now(timezone.utc) + PLAN_DURATIONS["trial"]
            db.commit()
            db.refresh(lic)
            return lic
        finally:
            db.close()

    @staticmethod
    def activate(user_id: int, license_key: str, plan: str = "monthly") -> dict:
        if plan not in PLAN_DURATIONS:
            return {"success": False, "error": "invalid_plan"}
        db = SessionLocal()
        try:
            lic = licenses_repo.create(db, user_id, license_key=license_key, plan=plan)
            duration = PLAN_DURATIONS[plan]
            lic.expires_at = (datetime.now(timezone.utc) + duration) if duration else None
            db.commit()
            db.refresh(lic)
            return {"success": True, "license": _public(lic)}
        finally:
            db.close()

    @staticmethod
    def current(user_id: int):
        db = SessionLocal()
        try:
            lic = licenses_repo.get_active_for_user(db, user_id)
            return _public(lic) if lic else None
        finally:
            db.close()
