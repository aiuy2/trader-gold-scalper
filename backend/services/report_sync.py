"""report_sync.py - server side of local-client/ws_client.py's outbound
reports. Each open /ws connection that starts sending {"report": {...}}
messages gets one LocalClientSession (created in server.py, lives for
the connection's lifetime).

A TradingWorker row is created lazily on the FIRST report, not on
connect - a plain browser/viewer connection only ever sends
{"subscribe": [...]} and never reports, so it never creates one. This
keeps trading_workers rows meaning "an engine actually ran" the same
way they did when only bot_service.py (mock, server-side) created them.
"""
from database.database import SessionLocal
from database.repositories import workers as workers_repo
from database.repositories import positions as positions_repo
from services.trade_sync import sync_outcome
from websocket.loop_registry import emit_threadsafe
from websocket import events as ws_events

_VALID_MODES = ("mock", "live")


class LocalClientSession:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.worker_row_id = None
        self.symbol = None
        self._known_tickets = set()


def handle_report(session: LocalClientSession, report: dict) -> None:
    outcome = report.get("data") or {}
    symbol = outcome.get("symbol") or session.symbol or "XAUUSD"
    mode = outcome.get("mode") if outcome.get("mode") in _VALID_MODES else "live"
    session.symbol = symbol

    db = SessionLocal()
    try:
        if session.worker_row_id is None:
            worker = workers_repo.create(db, session.user_id, symbol=symbol, mode=mode)
            session.worker_row_id = worker.id
            emit_threadsafe(ws_events.emit(session.user_id, ws_events.BOT_STATUS_CHANGED, {
                "running": True, "worker_id": session.worker_row_id, "mode": mode, "symbol": symbol,
            }))

        sync_outcome(db, session.user_id, session.worker_row_id, symbol, outcome, session._known_tickets)
    finally:
        db.close()


def end_session(session: LocalClientSession) -> None:
    """Called when the local-client's WebSocket connection drops (app
    closed, machine went to sleep, etc). Marks the worker stopped and
    clears its open-position rows - the positions themselves are still
    protected by their SL/TP on the broker side, this only affects what
    the web app displays."""
    if session.worker_row_id is None:
        return

    db = SessionLocal()
    try:
        worker_row = workers_repo.get_active_for_user(db, session.user_id)
        if worker_row and worker_row.id == session.worker_row_id:
            workers_repo.stop(db, worker_row)
        positions_repo.clear_for_worker(db, session.worker_row_id)
    finally:
        db.close()

    emit_threadsafe(ws_events.emit(session.user_id, ws_events.BOT_STATUS_CHANGED, {
        "running": False, "worker_id": session.worker_row_id,
    }))
