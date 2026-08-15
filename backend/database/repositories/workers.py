"""workers.py - trading worker CRUD."""
from sqlalchemy.orm import Session
from database.models.trading_worker import TradingWorker


def get_active_for_user(db: Session, user_id: int):
    return db.query(TradingWorker).filter(
        TradingWorker.user_id == user_id, TradingWorker.status == "running"
    ).first()


def create(db: Session, user_id: int, symbol: str, mode: str):
    worker = TradingWorker(user_id=user_id, symbol=symbol, mode=mode, status="running")
    from datetime import datetime, timezone
    worker.started_at = datetime.now(timezone.utc)
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


def stop(db: Session, worker: TradingWorker, error: str = None):
    from datetime import datetime, timezone
    worker.status = "error" if error else "stopped"
    worker.last_error = error
    worker.stopped_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(worker)
    return worker
