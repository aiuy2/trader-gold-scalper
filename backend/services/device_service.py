"""device_service.py - registers/lists/revokes a user's devices and enforces
the license's device-limit (see license-system/device_binding.py for the
standalone, non-backend version of this same rule)."""
from database.database import SessionLocal
from database.repositories import devices as devices_repo
from database.repositories import licenses as licenses_repo

PLAN_DEVICE_LIMITS = {"trial": 1, "monthly": 1, "yearly": 2, "lifetime": 3}


class DeviceService:
    @staticmethod
    def list_devices(user_id: int) -> list:
        db = SessionLocal()
        try:
            return [
                {
                    "device_id": d.device_id, "device_name": d.device_name,
                    "platform": d.platform, "last_seen": d.last_seen,
                }
                for d in devices_repo.list_for_user(db, user_id)
            ]
        finally:
            db.close()

    @staticmethod
    def register_device(user_id: int, device_id: str, device_name: str = None, platform: str = None) -> dict:
        db = SessionLocal()
        try:
            existing = devices_repo.get_by_device_id(db, user_id, device_id)
            if existing:
                devices_repo.touch(db, existing)
                return {"success": True, "device": existing.device_id}

            lic = licenses_repo.get_active_for_user(db, user_id)
            plan = lic.plan if lic else "trial"
            limit = PLAN_DEVICE_LIMITS.get(plan, 1)
            if len(devices_repo.list_for_user(db, user_id)) >= limit:
                return {"success": False, "error": "device_limit_reached", "limit": limit}

            device = devices_repo.create(db, user_id, device_id, device_name, platform)
            return {"success": True, "device": device.device_id}
        finally:
            db.close()

    @staticmethod
    def revoke_device(user_id: int, device_id: str) -> bool:
        db = SessionLocal()
        try:
            return devices_repo.delete(db, user_id, device_id)
        finally:
            db.close()
