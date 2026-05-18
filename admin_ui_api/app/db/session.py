from sqlalchemy.orm import sessionmaker

from app.db.base import engine

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    return SessionLocal()
