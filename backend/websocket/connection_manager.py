"""connection_manager.py - tracks open WebSocket connections per user so the
backend can push live trade/position/notification events to the mobile app."""
import threading

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._connections: dict = {}  # user_id -> set[WebSocket]
        self._lock = threading.Lock()

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        with self._lock:
            self._connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        with self._lock:
            conns = self._connections.get(user_id)
            if conns:
                conns.discard(websocket)
                if not conns:
                    self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict):
        with self._lock:
            conns = list(self._connections.get(user_id, ()))
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                self.disconnect(user_id, ws)


manager = ConnectionManager()
