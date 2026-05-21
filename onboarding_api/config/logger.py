import logging
import os
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from contextvars import ContextVar

load_dotenv()

# Context variable to store trace_id per logical context (request)
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="-")


class TraceContextFilter(logging.Filter):
    """Logging filter that injects the current trace_id from ContextVar into records."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            trace = trace_id_ctx.get()
        except LookupError:
            trace = None

        record.trace_id = trace if trace else "-"
        return True


def setup_logger(name: str) -> logging.Logger:

    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger(name)

    trace_filter = TraceContextFilter()

    # If handlers already exist, ensure they have the trace filter attached
    if logger.handlers:
        for h in logger.handlers:
            if not any(isinstance(f, TraceContextFilter) for f in h.filters):
                h.addFilter(trace_filter)
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | [trace_id=%(trace_id)s] | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(trace_filter)
    logger.addHandler(console_handler)

    # Info Log File
    info_handler = RotatingFileHandler(
        "logs/info.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    info_handler.addFilter(trace_filter)
    logger.addHandler(info_handler)

    # Debug Log File
    debug_enabled = os.getenv("DEBUG_LOG", "false").lower() == "true"

    if debug_enabled:
        debug_handler = RotatingFileHandler(
            "logs/debug.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)
        debug_handler.addFilter(trace_filter)
        logger.addHandler(debug_handler)

        logger.info("DEBUG logging ENABLED")

    else:
        logger.info("DEBUG logging DISABLED")

    return logger