"""statistics.py - dashboard stats endpoint."""
from fastapi import APIRouter, Depends

from database.models.user import User
from app.dependencies import get_current_user
from services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/summary")
def summary(user: User = Depends(get_current_user)):
    return StatisticsService.summary(user.id)
