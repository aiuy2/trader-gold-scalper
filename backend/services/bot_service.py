"""bot_service.py - starts/stops the trading-engine loop per user, in a
background thread, and mirrors its trades/positions into the database
so the mobile app and admin panel can read them via the API.

Runs the trading-engine module we already built under
trading-platform/trading-engine (imported by adding it to sys.path).
Defaults to the Mock MT5 connector so the whole flow — start bot from
the app, watch trades happen, stop bot — works without a live account.
"""
import os
import sys
import threading
import time

TRADING_ENGINE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "trading-platform", "trading-engine")
)
if TRADING_ENGINE_PATH not in sys.path:
    sys.path.insert(0, TRADING_ENGINE_PATH)

from database.database import SessionLocal
from database.repositories import workers as workers_repo
from database.repositories import trades as trades_repo
from database.repositories import positions as positions_repo
from database.repositories import bots as bots_repo
from websocket.loop_registry import emit_threadsafe
from websocket import events as ws_events


class BotRunner:
    """One running (or stopped) trading-engine instance for one user."""

    def __init__(self, user_id: int, mode: str = "mock"):
        self.user_id = user_id
        self.mode = mode
        self.symbol = "XAUUSD"
        self._thread = None
        self._stop_flag = threading.Event()
        self.worker_row_id = None
        self._known_tickets = set()

    def start(self):
        from main.engine import TradingEngine
        from mt5.connector import MockMT5Connector
        from risk.risk_manager import RiskManager

        db = SessionLocal()
        try:
            existing = workers_repo.get_active_for_user(db, self.user_id)
            if existing:
                return {"success": False, "error": "already_running", "worker_id": existing.id}

            config = bots_repo.get_or_create(db, self.user_id)
            if not config.is_enabled:
                return {"success": False, "error": "bot_disabled"}
            self.symbol = config.symbol or "XAUUSD"

            worker_row = workers_repo.create(db, self.user_id, symbol=self.symbol, mode=self.mode)
            self.worker_row_id = worker_row.id
        finally:
            db.close()

        connector = MockMT5Connector(symbol=self.symbol) if self.mode == "mock" else None
        if connector is None:
            raise ValueError("Live mode must be started with a real connector (see mt5/connector.py).")

        self.engine = TradingEngine(connector=connector)
        self.engine.symbol = self.symbol
        # Overlay this user's bot config (fixed lot / risk % / loss limits) on top
        # of the engine's default risk.json so each user's worker respects their
        # own settings from /bot/config, without editing the shared engine files.
        merged_risk_cfg = dict(self.engine.risk_cfg)
        merged_risk_cfg["risk"] = {
            **self.engine.risk_cfg.get("risk", {}),
            "fixed_lot": config.fixed_lot,
            "max_daily_loss_pct": config.max_daily_loss,
            "max_consecutive_losses": config.max_consecutive_losses,
        }
        self.engine.risk_manager = RiskManager(merged_risk_cfg)

        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        emit_threadsafe(ws_events.emit(self.user_id, ws_events.BOT_STATUS_CHANGED, {
            "running": True, "worker_id": self.worker_row_id, "mode": self.mode, "symbol": self.symbol,
        }))
        return {"success": True, "worker_id": self.worker_row_id}

    def _run_loop(self):
        db = SessionLocal()
        try:
            for outcome in self.engine.run(iterations=None, sleep_seconds=2):
                if self._stop_flag.is_set():
                    break
                self._sync_state(db, outcome)
        except Exception as exc:  # noqa: BLE001
            worker_row = workers_repo.get_active_for_user(db, self.user_id)
            if worker_row:
                workers_repo.stop(db, worker_row, error=str(exc))
        finally:
            db.close()

    def _sync_state(self, db, outcome):
        if outcome.get("action") == "opened_trade" and outcome.get("order_result", {}).get("success"):
            ticket = outcome["order_result"]["ticket"]
            if ticket not in self._known_tickets:
                self._known_tickets.add(ticket)
                trade = trades_repo.create(
                    db,
                    user_id=self.user_id,
                    worker_id=self.worker_row_id,
                    ticket=ticket,
                    symbol=self.symbol,
                    direction=outcome["direction"],
                    lot=outcome["trade_params"]["lot"],
                    entry_price=outcome["order_result"]["entry_price"],
                    stop_loss=outcome["trade_params"]["stop_loss"],
                    take_profit=outcome["trade_params"]["take_profit"],
                )
                positions_repo.create(
                    db,
                    user_id=self.user_id,
                    worker_id=self.worker_row_id,
                    ticket=ticket,
                    symbol=self.symbol,
                    direction=outcome["direction"],
                    lot=outcome["trade_params"]["lot"],
                    entry_price=outcome["order_result"]["entry_price"],
                    stop_loss=outcome["trade_params"]["stop_loss"],
                    take_profit=outcome["trade_params"]["take_profit"],
                )
                emit_threadsafe(ws_events.emit(self.user_id, ws_events.TRADE_OPENED, {
                    "ticket": ticket, "symbol": self.symbol, "direction": outcome["direction"],
                    "lot": trade.lot, "entry_price": trade.entry_price,
                }))

        elif outcome.get("action") == "closed_trade":
            ticket = outcome.get("ticket")
            close_result = outcome.get("close_result", {})
            exit_price = close_result.get("exit_price")
            pnl = outcome.get("pnl")

            trade = trades_repo.get_by_ticket(db, self.user_id, ticket)
            if trade and exit_price is not None:
                trades_repo.close(db, trade, exit_price=exit_price, pnl=pnl)
            positions_repo.delete_by_ticket(db, self.user_id, ticket)

            emit_threadsafe(ws_events.emit(self.user_id, ws_events.TRADE_CLOSED, {
                "ticket": ticket, "symbol": self.symbol, "reason": outcome.get("reason"),
                "pnl": pnl, "exit_price": exit_price,
            }))

    def stop(self):
        self._stop_flag.set()
        if self._thread:
            self._thread.join(timeout=5)
        db = SessionLocal()
        try:
            worker_row = workers_repo.get_active_for_user(db, self.user_id)
            if worker_row:
                workers_repo.stop(db, worker_row)
            positions_repo.clear_for_worker(db, self.worker_row_id)
        finally:
            db.close()
        emit_threadsafe(ws_events.emit(self.user_id, ws_events.BOT_STATUS_CHANGED, {
            "running": False, "worker_id": self.worker_row_id,
        }))
        return {"success": True}


class BotService:
    """Process-wide registry of running BotRunners, keyed by user_id."""

    _runners = {}
    _lock = threading.Lock()

    @classmethod
    def start(cls, user_id: int, mode: str = "mock"):
        with cls._lock:
            if user_id in cls._runners:
                return {"success": False, "error": "already_running"}
            runner = BotRunner(user_id, mode=mode)
            result = runner.start()
            if result["success"]:
                cls._runners[user_id] = runner
            return result

    @classmethod
    def stop(cls, user_id: int):
        with cls._lock:
            runner = cls._runners.pop(user_id, None)
            if not runner:
                return {"success": False, "error": "not_running"}
            return runner.stop()

    @classmethod
    def status(cls, user_id: int):
        with cls._lock:
            runner = cls._runners.get(user_id)
            return {"running": runner is not None, "worker_id": runner.worker_row_id if runner else None}
