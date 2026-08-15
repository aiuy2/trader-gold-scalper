"""user_service.py - current-user profile read/update + password change."""
from database.database import SessionLocal
from database.repositories import users as users_repo
from app.security import hash_password, verify_password


class UserService:
    @staticmethod
    def get_profile(user_id: int) -> dict:
        db = SessionLocal()
        try:
            user = users_repo.get_by_id(db, user_id)
            return {"id": user.id, "email": user.email, "full_name": user.full_name}
        finally:
            db.close()

    @staticmethod
    def update_profile(user_id: int, full_name: str = None) -> dict:
        db = SessionLocal()
        try:
            user = users_repo.get_by_id(db, user_id)
            if full_name is not None:
                user.full_name = full_name
            db.commit()
            db.refresh(user)
            return {"id": user.id, "email": user.email, "full_name": user.full_name}
        finally:
            db.close()

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> dict:
        db = SessionLocal()
        try:
            user = users_repo.get_by_id(db, user_id)
            if not verify_password(old_password, user.hashed_password):
                return {"success": False, "error": "wrong_password"}
            user.hashed_password = hash_password(new_password)
            db.commit()
            return {"success": True}
        finally:
            db.close()
