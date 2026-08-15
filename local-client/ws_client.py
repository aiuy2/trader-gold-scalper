"""ws_client.py - outbound reporter to the backend's existing /ws endpoint
(backend/websocket/server.py), so the web app keeps seeing live trade/
status updates even though the engine itself now runs on the user's
machine instead of in a backend thread.

Design choice: OUTBOUND only, from this client to the server - never the
other way around. The user's machine is typically behind NAT/a firewall
with no reachable public port, so the server can never open a connection
INTO it. This client dials out to the same /ws?token=... endpoint the
web frontend already uses (see backend/websocket/server.py), which is
firewall/NAT-friendly by construction.

Reporting is fire-and-forget from the trading loop's point of view:
run.py calls .report(...) and moves on immediately. A background thread
owns the actual socket and reconnects with backoff on its own; if the
link to the backend is down, events queue up in memory and flush once it
reconnects. None of this blocks or affects the trading loop - a lost
dashboard connection must never pause trading (only a lost *internet*
connection should - see connectivity.py).

NOTE (backend follow-up, not part of this change): backend/websocket/
server.py currently only understands inbound {"subscribe": [...]}
messages. For the backend to actually persist/rebroadcast the
{"report": {...}} messages this client sends, it needs a small addition
recognizing that message shape (store to DB + websocket/events.py-style
rebroadcast to the user's other connections, i.e. the web app). Until
that's added, this client will connect and send correctly, but the
backend will just ignore unrecognized messages rather than erroring -
so this file is safe to ship ahead of that backend change.
"""
import json
import queue
import threading
import time

import websocket  # pip install websocket-client


class WSReporter:
    def __init__(self, ws_url: str, on_command=None):
        self.ws_url = ws_url
        self.on_command = on_command  # optional callback(dict) for future inbound commands (start/stop/etc.)
        self._queue = queue.Queue()
        self._stop_flag = threading.Event()
        self._thread = None
        self._connected = threading.Event()

    def start(self):
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_flag.set()

    def report(self, event_type: str, data: dict):
        """Non-blocking - safe to call from the trading loop every tick."""
        self._queue.put({"report": {"type": event_type, "data": data}})

    def is_connected(self) -> bool:
        return self._connected.is_set()

    # -- internals --------------------------------------------------
    def _run_forever(self):
        backoff = 1.0
        while not self._stop_flag.is_set():
            try:
                self._connect_once()
                backoff = 1.0  # reset after a clean connection
            except Exception:  # noqa: BLE001
                pass
            self._connected.clear()
            if self._stop_flag.is_set():
                return
            time.sleep(backoff)
            backoff = min(backoff * 2, 30.0)

    def _connect_once(self):
        ws = websocket.create_connection(self.ws_url, timeout=8)
        self._connected.set()
        try:
            ws.settimeout(1.0)
            while not self._stop_flag.is_set():
                self._flush_queue(ws)
                try:
                    incoming = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                if incoming and self.on_command:
                    try:
                        self.on_command(json.loads(incoming))
                    except (json.JSONDecodeError, TypeError):
                        pass
        finally:
            ws.close()

    def _flush_queue(self, ws):
        while True:
            try:
                msg = self._queue.get_nowait()
            except queue.Empty:
                return
            ws.send(json.dumps(msg))
