import logging
import os
import contextvars
from logging.handlers import RotatingFileHandler
from typing import Optional

from dotenv import load_dotenv

load_dotenv()  # load .env file

# Context variable to hold current request trace id
current_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)


def set_trace_id(trace_id: Optional[str]):
    try:
        current_trace_id.set(trace_id)
    except Exception:
        pass


def get_trace_id() -> Optional[str]:
    try:
        return current_trace_id.get()
    except Exception:
        return None


def clear_trace_id():
    try:
        current_trace_id.set(None)
    except Exception:
        pass


class TraceIdFilter(logging.Filter):
    def filter(self, record):
        try:
            trace = current_trace_id.get()
        except Exception:
            trace = None

        record.trace_id = trace or "-"
        return True


def setup_logger(name: str) -> logging.Logger:

    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # capture all levels internally
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | trace=%(trace_id)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        # attach trace-id filter globally for this logger
        trace_filter = TraceIdFilter()
        logger.addFilter(trace_filter)

        # ── Handler 1: Console (INFO always on) ─────────────
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

        logger.info("Console logging handler initialized")

        # ── Handler 2: info.log (INFO always on) ────────────
        info_handler = RotatingFileHandler(
            "logs/info.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
        )

        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(formatter)

        logger.addHandler(info_handler)

        logger.info("INFO file logging handler initialized → logs/info.log")

        # ── Handler 3: debug.log (only if DEBUG_LOG=true) ───
        debug_enabled = os.getenv("DEBUG_LOG", "false").lower() == "true"

        logger.info(f"DEBUG_LOG environment value: {debug_enabled}")

        if debug_enabled:

            debug_handler = RotatingFileHandler(
                "logs/debug.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
            )

            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(formatter)

            logger.addHandler(debug_handler)

            logger.info("DEBUG logging is ENABLED → logs/debug.log")

        else:
            logger.info(
                "DEBUG logging is DISABLED "
                "(set DEBUG_LOG=true in .env to enable)"
            )

        logger.info(f"Logger initialized successfully for module: {name}")

    except Exception as e:
        logger.exception(f"Logger initialization failed for module {name}: {str(e)}")
        raise

    return logger