from pathlib import Path

from pydantic_settings import BaseSettings

from app.config.logger import setup_logger

logger = setup_logger(__name__)


class Settings(BaseSettings):

    logger.info("Initializing application settings")

    database_url: str = (
        "sqlite:///D:/OneDrive - REDINGTON/Work/Code/RAG/"
        "s1_rag_engine/sql_lite_db/rag_admin.sqlite3"
    )

    config_yaml_path: Path = (
        Path(__file__).resolve().parents[2] / "config.yaml"
    )

    logger.info("Application settings loaded successfully")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

logger.info("Global settings object initialized")