"""trading_service.py - read-only live trading snapshot (open positions,
whether the bot is running) for the current user. Complements bot_service.py,
which owns starting/stopping the bot; this just reports what it's doing now."""
from database.database import SessionLocal
from database.repositories import positions as positions_repo
from services.bot_service import BotService


class TradingService:
    @staticmethod
    def live_state(user_id: int) -> dict:
        status = BotService.status(user_id)
        db = SessionLocal()
        try:
            open_positions = positions_repo.list_for_user(db, user_id)
        finally:
            db.close()

        return {
            "running": status["running"],
            "worker_id": status["worker_id"],
            "open_positions_count": len(open_positions),
        }
