"""connection_manager.py - tracks open WebSocket connections per user so the
backend can push live trade/position/notification events to the mobile app,
and tags each connection with a `kind` (BROWSER or LOCAL_CLIENT) so a future
feature (e.g. a remote start/stop command) can target the desktop worker
specifically without also hitting a browser viewer tab.

Both kinds share the same /ws route/endpoint on purpose (see server.py's
docstring), so the kind isn't known at accept() time - a connection starts
as BROWSER and server.py calls mark_kind() to upgrade it to LOCAL_CLIENT the
moment it sends its first {"report": {...}} message. Until then, treating an
unlabeled connection as BROWSER is the safe default (it just means it won't
receive local-client-only messages, which don't exist yet anyway)."""
import threading

from fastapi import WebSocket

BROWSER = "browser"
LOCAL_CLIENT = "local_client"


class ConnectionManager:
    def __init__(self):
        self._connections: dict = {}  # user_id -> {WebSocket: kind}
        self._lock = threading.Lock()

    async def connect(self, user_id: int, websocket: WebSocket, kind: str = BROWSER):
        await websocket.accept()
        with self._lock:
            self._connections.setdefault(user_id, {})[websocket] = kind

    def mark_kind(self, user_id: int, websocket: WebSocket, kind: str) -> None:
        """Upgrade a connection's kind after accept() - see module docstring."""
        with self._lock:
            conns = self._connections.get(user_id)
            if conns and websocket in conns:
                conns[websocket] = kind

    def disconnect(self, user_id: int, websocket: WebSocket):
        with self._lock:
            conns = self._connections.get(user_id)
            if conns:
                conns.pop(websocket, None)
                if not conns:
                    self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict, kind: str = None):
        """kind=None (default) broadcasts to every connection for this user,
        regardless of type - this is what every existing caller (events.py's
        emit()) wants, since trade/position/notification updates are for
        whatever is watching, browser or local client. Pass kind=BROWSER or
        kind=LOCAL_CLIENT to target only that subset."""
        with self._lock:
            conns = list(self._connections.get(user_id, {}).items())
        for ws, ws_kind in conns:
            if kind is not None and ws_kind != kind:
                continue
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                self.disconnect(user_id, ws)

    async def send_to_local_client(self, user_id: int, message: dict):
        """Convenience wrapper for the local-client-only case described in
        the module docstring - e.g. a future POST /bot/stop could use this to
        make sure the command reaches the desktop worker and not a browser
        tab that happens to share the connection type."""
        await self.send_to_user(user_id, message, kind=LOCAL_CLIENT)

    def has_local_client(self, user_id: int) -> bool:
        """True if this user currently has a local-client (desktop worker)
        connection open, as opposed to only browser/viewer tabs."""
        with self._lock:
            return any(k == LOCAL_CLIENT for k in self._connections.get(user_id, {}).values())


manager = ConnectionManager()
