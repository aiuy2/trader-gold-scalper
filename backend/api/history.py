"""history.py - trade history with basic filtering (symbol, date range)."""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.trade import Trade
from database.models.user import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
def get_history(
    symbol: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Trade).filter(Trade.user_id == user.id)
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    if date_from:
        query = query.filter(Trade.opened_at >= date_from)
    if date_to:
        query = query.filter(Trade.opened_at <= date_to)
    return query.order_by(Trade.opened_at.desc()).limit(limit).all()
