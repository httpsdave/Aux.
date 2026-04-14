from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BACKEND_DIR / "data" / "aux.db"


class Settings(BaseSettings):
    app_name: str = "Aux. API"
    database_url: str = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    chart_name: str = "hot-100"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
