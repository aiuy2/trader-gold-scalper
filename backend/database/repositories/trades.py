"""trades.py - trade history CRUD."""
from sqlalchemy.orm import Session
from database.models.trade import Trade


def list_for_user(db: Session, user_id: int, limit: int = 100):
    return (
        db.query(Trade)
        .filter(Trade.user_id == user_id)
        .order_by(Trade.opened_at.desc())
        .limit(limit)
        .all()
    )


def get_by_ticket(db: Session, user_id: int, ticket: int):
    return (
        db.query(Trade)
        .filter(Trade.user_id == user_id, Trade.ticket == ticket)
        .first()
    )


def create(db: Session, **kwargs):
    trade = Trade(**kwargs)
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def close(db: Session, trade: Trade, exit_price: float, pnl: float):
    from datetime import datetime, timezone
    trade.exit_price = exit_price
    trade.pnl = pnl
    trade.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(trade)
    return trade
