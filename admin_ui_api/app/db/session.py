from sqlalchemy.orm import sessionmaker

from app.config.logger import setup_logger
from app.db.base import engine

logger = setup_logger(__name__)

logger.info("Database session module initialization started")

try:
    logger.debug("Creating SQLAlchemy session factory")

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False
    )

    logger.info("SQLAlchemy session factory created successfully")

except Exception as e:
    logger.exception(f"Session factory initialization failed: {str(e)}")
    raise


def get_session():
    logger.debug("Database session requested")

    try:
        session = SessionLocal()

        logger.info("Database session created successfully")

        return session

    except Exception as e:
        logger.exception(f"Database session creation failed: {str(e)}")
        raise