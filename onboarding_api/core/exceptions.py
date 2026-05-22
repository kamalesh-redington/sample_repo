import logging
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .response import format_response

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPException and return standardized response."""
    try:
        trace_id = request.headers.get("trace_id") or "-"
    except Exception:
        trace_id = "-"

    content = format_response(
        status="error",
        statu_code=str(exc.status_code),
        status_message=str(exc.detail) if exc.detail else "HTTP Error",
        response=[],
        trace_id=trace_id,
    )

    logger.warning("HTTPException handled: %s %s", exc.status_code, exc.detail)

    return JSONResponse(status_code=exc.status_code, content=content)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors and return standardized response."""
    try:
        trace_id = request.headers.get("trace_id") or "-"
    except Exception:
        trace_id = "-"

    content = format_response(
        status="error",
        statu_code="422",
        status_message="Validation Error",
        response=[],
        trace_id=trace_id,
    )

    logger.warning("RequestValidationError: %s", exc)

    return JSONResponse(status_code=422, content=content)


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions and return standardized response."""
    try:
        trace_id = request.headers.get("trace_id") or "-"
    except Exception:
        trace_id = "-"

    logger.exception("Unhandled exception: %s", exc)

    content = format_response(
        status="error",
        statu_code="500",
        status_message="Internal Server Error",
        response=[],
        trace_id=trace_id,
    )

    return JSONResponse(status_code=500, content=content)
