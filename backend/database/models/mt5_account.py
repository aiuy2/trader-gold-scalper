"""mt5_account.py - a linked MT5 trading account. Password is stored
encrypted (see backend/security/encryption.py); never stored/logged in plaintext."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from database.database import Base


class MT5Account(Base):
    __tablename__ = "mt5_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    login = Column(String, nullable=False)
    encrypted_password = Column(String, nullable=False)
    server = Column(String, nullable=False)
    broker = Column(String, nullable=True)
    is_live = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
