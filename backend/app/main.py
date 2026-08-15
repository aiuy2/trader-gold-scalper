"""main.py - FastAPI application entrypoint.

Run locally:
    pip install -r requirements.txt
    uvicorn backend.app.main:app --reload --port 8000

Then open http://localhost:8000/docs for interactive API docs.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.database import init_db
from api import (
    auth, bot, trades, positions, health,
    accounts, users, history, licenses, devices,
    statistics, settings as settings_api, trading, notifications,
)
from middleware.error_handler import register_error_handlers
from middleware.request_logger import RequestLoggerMiddleware
from middleware.rate_limit import RateLimitMiddleware
from websocket.server import router as websocket_router

app = FastAPI(title="TRADER GOLD SCALPER API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before production
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggerMiddleware)

register_error_handlers(app)

# core
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(bot.router)
app.include_router(trades.router)
app.include_router(positions.router)

# phase 1 additions
app.include_router(accounts.router)
app.include_router(users.router)
app.include_router(history.router)
app.include_router(licenses.router)
app.include_router(devices.router)
app.include_router(statistics.router)
app.include_router(settings_api.router)
app.include_router(trading.router)
app.include_router(notifications.router)

# realtime
app.include_router(websocket_router)


@app.on_event("startup")
def on_startup():
    init_db()
    import asyncio
    from websocket.loop_registry import set_loop
    set_loop(asyncio.get_event_loop())
