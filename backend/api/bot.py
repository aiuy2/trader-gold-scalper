"""bot.py - start/stop/status control for the user's trading bot, plus the
bot's own configuration (symbol, lot mode, risk %, max daily loss, max
consecutive losses). Config is separate from /settings (which holds general
app/UI preferences) and from the runtime TradingWorker status rows."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.user import User
from database.repositories import bots as bots_repo
from app.dependencies import get_current_user
from services.bot_service import BotService

router = APIRouter(prefix="/bot", tags=["bot"])


class StartRequest(BaseModel):
    mode: str = "mock"  # "mock" for now; "live" once a live MT5 connector is wired in


class BotConfigUpdateRequest(BaseModel):
    symbol: str | None = None
    lot_mode: str | None = None          # fixed | dynamic
    fixed_lot: float | None = None
    risk_percent: float | None = None
    max_daily_loss: float | None = None
    max_consecutive_losses: int | None = None
    is_enabled: bool | None = None


@router.post("/start")
def start_bot(payload: StartRequest, user: User = Depends(get_current_user)):
    return BotService.start(user.id, mode=payload.mode)


@router.post("/stop")
def stop_bot(user: User = Depends(get_current_user)):
    return BotService.stop(user.id)


@router.get("/status")
def bot_status(user: User = Depends(get_current_user)):
    return BotService.status(user.id)


@router.get("/config")
def get_bot_config(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return bots_repo.get_or_create(db, user.id)


@router.patch("/config")
def update_bot_config(
    payload: BotConfigUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return bots_repo.update(db, user.id, **payload.model_dump())
