"""notification.py - in-app notification (trade opened/closed, risk alert,
mt5 disconnected, etc.) shown in the mobile app's inbox."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from database.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)     # trade_opened | trade_closed | risk_alert | ...
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
