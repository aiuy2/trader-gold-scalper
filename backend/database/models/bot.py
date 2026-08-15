"""bot.py - per-user bot CONFIGURATION (risk %, lot mode, symbol, on/off).
Distinct from TradingWorker (database/models/trading_worker.py), which is
the *runtime* record of a single start/stop run."""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func
from database.database import Base


class BotConfig(Base):
    __tablename__ = "bot_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    symbol = Column(String, default="XAUUSD")
    lot_mode = Column(String, default="fixed")     # fixed | dynamic
    fixed_lot = Column(Float, default=0.01)
    risk_percent = Column(Float, default=1.0)
    max_daily_loss = Column(Float, default=5.0)
    max_consecutive_losses = Column(Integer, default=3)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)
