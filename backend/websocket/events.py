"""events.py - event type constants + a helper to broadcast an event to a
user's connected WebSocket clients."""
from websocket.connection_manager import manager

TRADE_OPENED = "trade_opened"
TRADE_CLOSED = "trade_closed"
POSITION_UPDATED = "position_updated"
BOT_STATUS_CHANGED = "bot_status_changed"
NOTIFICATION = "notification"


async def emit(user_id: int, event_type: str, payload: dict):
    await manager.send_to_user(user_id, {"type": event_type, "data": payload})
