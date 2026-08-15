"""trading_worker.py - one running instance of the trading engine for a user."""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func
from database.database import Base


class TradingWorker(Base):
    __tablename__ = "trading_workers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, default="XAUUSD")
    status = Column(String, default="stopped")  # stopped | running | error
    mode = Column(String, default="mock")        # mock | live
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
