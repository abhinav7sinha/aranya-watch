"""Application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_name: str = "aranya-watch"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/"
    preview_mode: bool = Field(default=False, alias="PREVIEW_MODE")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/aranya_watch",
        alias="DATABASE_URL",
    )
    firms_api_key: str = Field(default="", alias="FIRMS_API_KEY")
    firms_base_url: str = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    firms_source: str = "VIIRS_SNPP_NRT"
    firms_day_range: int = 1
    default_recent_limit: int = 50
    max_recent_limit: int = 500
    request_timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
