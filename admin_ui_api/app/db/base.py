from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

from app.config.logger import setup_logger
from app.core.config import settings

logger = setup_logger(__name__)

logger.info("Database engine initialization started")

try:
    logger.debug(
        f"Creating SQLAlchemy engine for database URL: {settings.database_url}"
    )

    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False}
    )

    logger.info("Database engine created successfully")

    logger.debug("Initializing SQLAlchemy declarative base")

    Base = declarative_base()

    logger.info("SQLAlchemy declarative base initialized successfully")

except Exception as e:
    logger.exception(f"Database base initialization failed: {str(e)}")
    raise