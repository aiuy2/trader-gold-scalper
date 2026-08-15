"""trading.py - live trading snapshot for the current user's running bot."""
from fastapi import APIRouter, Depends

from database.models.user import User
from app.dependencies import get_current_user
from services.trading_service import TradingService

router = APIRouter(prefix="/trading", tags=["trading"])


@router.get("/live")
def live_state(user: User = Depends(get_current_user)):
    return TradingService.live_state(user.id)
