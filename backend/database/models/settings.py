"""settings.py - per-user app + risk preferences (one row per user)."""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func
from database.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    risk_percent = Column(Float, default=1.0)
    max_daily_loss = Column(Float, default=5.0)
    notifications_enabled = Column(Boolean, default=True)
    theme = Column(String, default="dark")
    language = Column(String, default="ar")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
