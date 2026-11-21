from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    web_origin: str = Field(default="http://localhost:3000", alias="WEB_ORIGIN")
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")
    app_name: str = "ai-teacher-api"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("database_url")
    @classmethod
    def require_postgres(cls, value: str) -> str:
        if not value.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL.")
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_level(cls, value: str) -> str:
        upper = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if upper not in allowed:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL.")
        return upper

    @field_validator("web_origin")
    @classmethod
    def strip_origin(cls, value: str) -> str:
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def safe_database_target(database_url: str) -> dict[str, str | int | None]:
    parts = urlsplit(database_url)
    return {
        "scheme": parts.scheme,
        "host": parts.hostname,
        "port": parts.port,
        "database": parts.path.lstrip("/") or None,
    }
