"""Database configuration and session management.

This module provides database agnostic setup using SQLAlchemy.
Supports SQLite, PostgreSQL, MySQL, and other databases via connection string.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Generator

# Database configuration - using SQLite for now
# Can be easily switched to PostgreSQL, MySQL, etc. via DATABASE_URL environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///D:/s1_rag_engine/sql_lite_db/rag_admin.sqlite3"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,  # Set to True for SQL debug logging
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


def get_db() -> Generator:
    """Dependency injection for database session in FastAPI routes.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables defined in models.
    
    Call this once at startup to create tables if they don't exist.
    """
    Base.metadata.create_all(bind=engine)
