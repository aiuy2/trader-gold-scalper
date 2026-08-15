"""license.py - subscription/license record for a user."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from database.database import Base


class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    license_key = Column(String, unique=True, index=True, nullable=False)
    plan = Column(String, default="trial")  # trial | monthly | yearly | lifetime
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    device_id = Column(String, nullable=True)
