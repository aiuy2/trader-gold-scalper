"""trade_sync.py - turns one TradingEngine outcome dict into the DB
writes + websocket broadcast. Shared by two callers so they never drift
apart:

  - bot_service.py's BotRunner._run_loop - engine running IN this
    process (mock mode, background thread)
  - report_sync.py - engine running on the user's own machine via
    local-client/run.py, each outcome relayed here over the existing
    /ws endpoint as a {"report": {...}} message
"""
from database.repositories import trades as trades_repo
from database.repositories import positions as positions_repo
from websocket.loop_registry import emit_threadsafe
from websocket import events as ws_events


def sync_outcome(db, user_id: int, worker_id: int, symbol: str, outcome: dict, known_tickets: set) -> None:
    action = outcome.get("action")

    if action == "opened_trade" and outcome.get("order_result", {}).get("success"):
        ticket = outcome["order_result"]["ticket"]
        if ticket in known_tickets:
            return
        known_tickets.add(ticket)

        trade = trades_repo.create(
            db, user_id=user_id, worker_id=worker_id, ticket=ticket, symbol=symbol,
            direction=outcome["direction"], lot=outcome["trade_params"]["lot"],
            entry_price=outcome["order_result"]["entry_price"],
            stop_loss=outcome["trade_params"]["stop_loss"],
            take_profit=outcome["trade_params"]["take_profit"],
        )
        positions_repo.create(
            db, user_id=user_id, worker_id=worker_id, ticket=ticket, symbol=symbol,
            direction=outcome["direction"], lot=outcome["trade_params"]["lot"],
            entry_price=outcome["order_result"]["entry_price"],
            stop_loss=outcome["trade_params"]["stop_loss"],
            take_profit=outcome["trade_params"]["take_profit"],
        )
        emit_threadsafe(ws_events.emit(user_id, ws_events.TRADE_OPENED, {
            "ticket": ticket, "symbol": symbol, "direction": outcome["direction"],
            "lot": trade.lot, "entry_price": trade.entry_price,
        }))

    elif action == "closed_trade":
        ticket = outcome.get("ticket")
        close_result = outcome.get("close_result", {})
        exit_price = close_result.get("exit_price")
        pnl = outcome.get("pnl")

        trade = trades_repo.get_by_ticket(db, user_id, ticket)
        if trade and exit_price is not None:
            trades_repo.close(db, trade, exit_price=exit_price, pnl=pnl)
        positions_repo.delete_by_ticket(db, user_id, ticket)

        emit_threadsafe(ws_events.emit(user_id, ws_events.TRADE_CLOSED, {
            "ticket": ticket, "symbol": symbol, "reason": outcome.get("reason"),
            "pnl": pnl, "exit_price": exit_price,
        }))

    elif action == "offline_paused":
        # local-client only (see local-client/connectivity.py) - the user's
        # machine has no internet route, so no new trade can be opened.
        emit_threadsafe(ws_events.emit(user_id, ws_events.NOTIFICATION, {
            "level": "warning",
            "message": "الجهاز المحلي فقد الاتصال بالإنترنت - تم إيقاف فتح صفقات جديدة مؤقتًا.",
        }))

    elif action == "connector_unhealthy":
        emit_threadsafe(ws_events.emit(user_id, ws_events.NOTIFICATION, {
            "level": "warning",
            "message": "فقد الاتصال بمنصة MT5 - تم إيقاف فتح صفقات جديدة مؤقتًا.",
        }))
