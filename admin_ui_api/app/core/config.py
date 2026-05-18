from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./rag_admin.sqlite3"
    config_yaml_path: Path = Path(__file__).resolve().parents[2] / "config.yaml"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
