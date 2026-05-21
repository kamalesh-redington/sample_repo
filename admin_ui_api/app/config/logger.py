import logging
import os
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

load_dotenv()  # load .env file


def setup_logger(name: str) -> logging.Logger:

    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # capture all levels internally
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    try:
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
            backupCount=3
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
                backupCount=3
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