"""position.py - a currently open position (mirrors broker state)."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from database.database import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("trading_workers.id"), nullable=True)
    ticket = Column(Integer, nullable=False)
    symbol = Column(String, default="XAUUSD")
    direction = Column(String)
    lot = Column(Float)
    entry_price = Column(Float)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
