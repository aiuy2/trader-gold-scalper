"""rate_limit.py - simple in-memory fixed-window rate limiter middleware.
Good enough for a single-process deployment; swap for Redis if you scale
out to multiple backend workers/instances."""
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

WINDOW_SECONDS = 60
MAX_REQUESTS = 120

_hits: dict = defaultdict(deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        client_id = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = _hits[client_id]
        while bucket and now - bucket[0] > WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= MAX_REQUESTS:
            return JSONResponse(status_code=429, content={"detail": "Too many requests, slow down."})
        bucket.append(now)
        return await call_next(request)
