"""bots.py - per-user bot configuration CRUD (risk %, lot mode, symbol) —
separate from trading_workers, which is the *runtime* status of a bot run."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database.models.bot import BotConfig


def get_for_user(db: Session, user_id: int):
    return db.query(BotConfig).filter(BotConfig.user_id == user_id).first()


def get_or_create(db: Session, user_id: int) -> BotConfig:
    row = get_for_user(db, user_id)
    if row:
        return row
    row = BotConfig(user_id=user_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update(db: Session, user_id: int, **fields) -> BotConfig:
    row = get_or_create(db, user_id)
    for key, value in fields.items():
        if value is not None and hasattr(row, key):
            setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row
