"""worker_service.py - history view over trading_workers (past + present
runs of a user's bot), distinct from bot_service.py which manages the
live in-process runner."""
from sqlalchemy import desc

from database.database import SessionLocal
from database.models.trading_worker import TradingWorker


class WorkerService:
    @staticmethod
    def history(user_id: int, limit: int = 50) -> list:
        db = SessionLocal()
        try:
            rows = (
                db.query(TradingWorker)
                .filter(TradingWorker.user_id == user_id)
                .order_by(desc(TradingWorker.created_at))
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id, "symbol": r.symbol, "status": r.status, "mode": r.mode,
                    "started_at": r.started_at, "stopped_at": r.stopped_at,
                    "last_error": r.last_error,
                }
                for r in rows
            ]
        finally:
            db.close()
