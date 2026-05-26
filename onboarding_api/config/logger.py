import logging
import os
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import sys

load_dotenv()

# Force UTF-8 console output
sys.stdout.reconfigure(encoding="utf-8")


def setup_logger(name: str) -> logging.Logger:

    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # ==========================================
    # Console Handler (UTF-8 SAFE)
    # ==========================================

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Info Log File
    info_handler = RotatingFileHandler(
        "logs/info.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
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
        logger.addHandler(debug_handler)

        logger.info("DEBUG logging ENABLED")

    else:
        logger.info("DEBUG logging DISABLED")

    return logger