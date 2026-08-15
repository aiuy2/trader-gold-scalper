"""settings.py - get/update the user's bot risk settings + app preferences."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.repositories import settings as settings_repo
from database.models.user import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdateRequest(BaseModel):
    risk_percent: float | None = None
    max_daily_loss: float | None = None
    notifications_enabled: bool | None = None
    theme: str | None = None
    language: str | None = None


@router.get("")
def get_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return settings_repo.get_or_create(db, user.id)


@router.patch("")
def update_settings(
    payload: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return settings_repo.update(db, user.id, **payload.model_dump())
