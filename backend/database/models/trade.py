"""trade.py - a closed trade (for history/statistics)."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from database.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("trading_workers.id"), nullable=True)
    ticket = Column(Integer, nullable=True)
    symbol = Column(String, default="XAUUSD")
    direction = Column(String)  # buy | sell
    lot = Column(Float)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
