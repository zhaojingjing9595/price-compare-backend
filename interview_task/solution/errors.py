"""Translation of domain errors into HTTP responses.

The service layer raises plain domain errors and stays unaware of HTTP — the same
`StoreUnavailableError` is consumed by a background backfill, which has no response
to return. Mapping them to status codes happens here, at the edge, and nowhere else.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from services.store_client import StoreDataError, StoreUnavailableError

logger = logging.getLogger(__name__)


async def store_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Any failure talking to a store becomes a 503, instead of a try/except per route."""
    logger.warning("store call failed on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The store is currently unavailable"},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Wire domain errors to responses. Called once from main.py."""
    for exc_type in (StoreUnavailableError, StoreDataError):
        app.add_exception_handler(exc_type, store_error_handler)
