"""Database configuration and session management.

This module provides database agnostic setup using SQLAlchemy.
Supports SQLite, PostgreSQL, MySQL, and other databases via connection string.
"""
from config.logger import setup_logger
logger = setup_logger(__name__)
from config.timer import log_execution_time

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Generator
from dotenv import load_dotenv
import os

load_dotenv()
# Database configuration - using SQLite for now
# Can be easily switched to PostgreSQL, MySQL, etc. via DATABASE_URL environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    #"sqlite:///D:/s1_rag_engine/sql_lite_db/rag_admin.sqlite3"
)
logger.info("Loading database configuration")
logger.debug(f"Database URL configured: {DATABASE_URL}")

''' # if databse url is with password
safe_db_url = DATABASE_URL.split("@")[-1]

logger.debug(
    f"Database target configured: {safe_db_url}"
)
'''

# Create engine
logger.info("Creating SQLAlchemy engine")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,  # Set to True for SQL debug logging
)
logger.debug("SQLAlchemy engine created successfully")

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
logger.debug("SessionLocal configured")
# Base class for models
Base = declarative_base()


@log_execution_time(logger)
def get_db() -> Generator:
    logger.debug("Creating database session")
    """Dependency injection for database session in FastAPI routes.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        logger.debug("Database session created successfully")
        yield db
    finally:
        logger.debug("Closing database session")
        db.close()


@log_execution_time(logger)
def init_db():

    try:

        logger.info("Initializing database tables")

        Base.metadata.create_all(bind=engine)

        logger.info(
            "Database tables initialized successfully"
        )

        logger.debug(
            "SQLAlchemy metadata synchronized"
        )

    except Exception as e:

        logger.exception(
            "Database initialization failed"
        )

        raise