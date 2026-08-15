"""request_logger.py - logs method/path/status/duration for every request."""
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("trader_gold_scalper.requests")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method, request.url.path, response.status_code, duration_ms,
        )
        return response
