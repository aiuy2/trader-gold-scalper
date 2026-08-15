"""trades.py - trade history for the current user."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from database.repositories import trades as trades_repo
from database.models.user import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("")
def list_trades(limit: int = 100, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return trades_repo.list_for_user(db, user.id, limit=limit)
