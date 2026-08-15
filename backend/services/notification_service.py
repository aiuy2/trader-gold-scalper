"""notification_service.py - in-app notification CRUD (paired with
notifications/push/* for actual push delivery; this is the DB-backed inbox
the mobile app reads/polls, and can also be pushed live over the websocket)."""
from database.database import SessionLocal
from database.models.notification import Notification


class NotificationService:
    @staticmethod
    def create(user_id: int, type_: str, title: str, message: str) -> Notification:
        db = SessionLocal()
        try:
            note = Notification(user_id=user_id, type=type_, title=title, message=message)
            db.add(note)
            db.commit()
            db.refresh(note)
            return note
        finally:
            db.close()

    @staticmethod
    def list_for_user(user_id: int, unread_only: bool = False, limit: int = 50) -> list:
        db = SessionLocal()
        try:
            query = db.query(Notification).filter(Notification.user_id == user_id)
            if unread_only:
                query = query.filter(Notification.is_read == False)  # noqa: E712
            return query.order_by(Notification.created_at.desc()).limit(limit).all()
        finally:
            db.close()

    @staticmethod
    def mark_read(user_id: int, notification_id: int) -> bool:
        db = SessionLocal()
        try:
            note = db.query(Notification).filter(
                Notification.id == notification_id, Notification.user_id == user_id
            ).first()
            if not note:
                return False
            note.is_read = True
            db.commit()
            return True
        finally:
            db.close()
