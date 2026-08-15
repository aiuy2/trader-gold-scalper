"""device.py - a device registered/trusted for a user's account (used for
license device-binding and the mobile app's 'active devices' list)."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, func
from database.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(String, index=True, nullable=False)   # stable client-generated UUID
    device_name = Column(String, nullable=True)
    platform = Column(String, nullable=True)                 # ios | android
    is_trusted = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
