"""accounts.py - linked MT5 trading account CRUD (encrypted password at rest)."""
from sqlalchemy.orm import Session
from database.models.mt5_account import MT5Account


def list_for_user(db: Session, user_id: int):
    return db.query(MT5Account).filter(MT5Account.user_id == user_id).all()


def get(db: Session, user_id: int, account_id: int):
    return db.query(MT5Account).filter(
        MT5Account.user_id == user_id, MT5Account.id == account_id
    ).first()


def create(db: Session, user_id: int, login: str, encrypted_password: str, server: str,
           broker: str = "", is_live: bool = False):
    account = MT5Account(
        user_id=user_id, login=login, encrypted_password=encrypted_password,
        server=server, broker=broker, is_live=is_live, is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def delete(db: Session, user_id: int, account_id: int) -> bool:
    deleted = db.query(MT5Account).filter(
        MT5Account.user_id == user_id, MT5Account.id == account_id
    ).delete()
    db.commit()
    return deleted > 0
