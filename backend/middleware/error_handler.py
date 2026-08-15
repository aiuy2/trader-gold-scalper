"""error_handler.py - converts unhandled exceptions into a clean JSON 500
instead of leaking a stack trace to the client, and logs them server-side."""
import logging
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("trader_gold_scalper.errors")


def register_error_handlers(app):
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled error on %s: %s\n%s", request.url.path, exc, traceback.format_exc()
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again later."},
        )
