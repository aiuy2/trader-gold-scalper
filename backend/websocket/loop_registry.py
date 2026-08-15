"""loop_registry.py - lets background threads (bot_service.py's per-user
trading loop) schedule an async websocket emit() onto the FastAPI app's
event loop. Without this, calling an `async def` from a plain background
thread has no event loop to run on and would silently do nothing (or
raise) instead of delivering the message.

Set once at startup (see app/main.py's on_startup hook); read from
anywhere, including other threads.
"""
import asyncio
import threading

_lock = threading.Lock()
_loop: asyncio.AbstractEventLoop = None


def set_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    with _lock:
        _loop = loop


def emit_threadsafe(coro) -> None:
    """Schedules an emit()-style coroutine from any thread. No-ops (and
    logs) if called before the loop is registered or after it's closed -
    e.g. a bot loop tick that races app shutdown - since a dropped
    real-time UI update should never crash the trading loop itself."""
    with _lock:
        loop = _loop
    if loop is None or loop.is_closed():
        coro.close()
        return
    try:
        asyncio.run_coroutine_threadsafe(coro, loop)
    except RuntimeError:
        coro.close()
