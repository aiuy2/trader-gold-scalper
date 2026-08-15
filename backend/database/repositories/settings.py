"""settings.py - per-user app/risk settings CRUD (get-or-create pattern)."""
from sqlalchemy.orm import Session
from database.models.settings import UserSettings


def get_for_user(db: Session, user_id: int):
    return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()


def get_or_create(db: Session, user_id: int) -> UserSettings:
    row = get_for_user(db, user_id)
    if row:
        return row
    row = UserSettings(user_id=user_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update(db: Session, user_id: int, **fields) -> UserSettings:
    row = get_or_create(db, user_id)
    for key, value in fields.items():
        if value is not None and hasattr(row, key):
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row
