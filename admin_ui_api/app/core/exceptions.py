from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config.logger import setup_logger, get_trace_id
from app.utils.response import format_response

logger = setup_logger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException handled: {exc.detail}")
    trace = get_trace_id()
    return JSONResponse(
        status_code=exc.status_code,
        content=format_response(
            status="error",
            statu_code=str(exc.status_code),
            status_message=str(exc.detail),
            response=[],
            trace_id=trace,
        ),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc}")
    trace = get_trace_id()
    # collect error messages
    try:
        errors = exc.errors()
    except Exception:
        errors = str(exc)

    return JSONResponse(
        status_code=422,
        content=format_response(
            status="error",
            statu_code="422",
            status_message="Validation Error",
            response=[],
            trace_id=trace,
        ),
    )


async def internal_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    trace = get_trace_id()
    return JSONResponse(
        status_code=500,
        content=format_response(
            status="error",
            statu_code="500",
            status_message="Internal Server Error",
            response=[],
            trace_id=trace,
        ),
    )
