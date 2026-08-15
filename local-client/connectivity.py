"""connectivity.py - internet-reachability guard for the local client.

This is a *separate, earlier* check than
engine/protection/mt5_monitor.py:is_connector_healthy(). That one asks
the MT5 terminal itself "are you healthy" (which can be slow, or can
briefly still answer from a local cache even with no internet). This
one asks a much cheaper, more direct question first: "does this machine
have a route to the outside internet at all right now?" - a plain TCP
handshake to a small set of well-known hosts, no HTTP request, no
dependency beyond the standard library.

ConnectivityGuard.is_online() is checked in main.py *before* letting the
engine take a single step, so:
  - offline -> the engine is never even asked for a signal -> no new
    trades can be opened, full stop.
  - a position that's already open is unaffected: its stop-loss and
    take-profit live on the broker/MT5 server side already (see
    connector.place_order sending sl/tp in the same request), so it's
    protected independently of whether this Python process is running
    at all.
"""
import socket
import time

# A short, deliberately redundant list: any one of these being reachable
# is enough to call the machine "online". Using more than one avoids a
# false "offline" if a single host/port is temporarily blocked/down.
_PROBE_TARGETS = [
    ("1.1.1.1", 443),
    ("8.8.8.8", 443),
    ("9.9.9.9", 443),
]


class ConnectivityGuard:
    def __init__(self, api_host: str = None, api_port: int = 443, timeout_seconds: float = 3.0):
        self.timeout_seconds = timeout_seconds
        self._targets = list(_PROBE_TARGETS)
        if api_host:
            # Also probe the trading backend's own host - catches cases
            # where general internet is fine but this specific service
            # (or the user's firewall) is the problem.
            self._targets.insert(0, (api_host, api_port))

        self._last_check_at = 0.0
        self._last_result = False
        self._min_check_interval = 1.0  # don't hammer sockets every loop tick

    def is_online(self) -> bool:
        now = time.monotonic()
        if now - self._last_check_at < self._min_check_interval:
            return self._last_result

        online = any(self._can_reach(host, port) for host, port in self._targets)
        self._last_check_at = now
        self._last_result = online
        return online

    def _can_reach(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=self.timeout_seconds):
                return True
        except OSError:
            return False
