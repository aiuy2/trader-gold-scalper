"""positions.py - currently open positions for the current user."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from database.repositories import positions as positions_repo
from database.models.user import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("")
def list_positions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return positions_repo.list_for_user(db, user.id)
