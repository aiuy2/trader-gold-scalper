"""database.py - SQLAlchemy engine/session setup.

Defaults to a local SQLite file so the backend runs with zero external
setup. Point DB_URL (in .env) at Postgres/MySQL for production.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {"check_same_thread": False} if settings.DB_URL.startswith("sqlite") else {}
engine = create_engine(settings.DB_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # import models so they're registered on Base before create_all
    from database.models import (  # noqa
        user, trade, position, trading_worker, license as license_model,
        device, mt5_account, settings as settings_model, notification, bot as bot_model,
    )
    Base.metadata.create_all(bind=engine)
