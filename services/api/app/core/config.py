from decimal import Decimal
from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    web_origin: str = Field(default="http://localhost:3000", alias="WEB_ORIGIN")
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_budget_usd: Decimal = Field(default=Decimal("20"), alias="GEMINI_BUDGET_USD")
    gemini_timeout_seconds: float = Field(default=20, alias="GEMINI_TIMEOUT_SECONDS")
    gemini_max_output_tokens: int = Field(default=256, alias="GEMINI_MAX_OUTPUT_TOKENS")
    gemini_max_retries: int = Field(default=1, alias="GEMINI_MAX_RETRIES")
    gemini_max_calls_per_action: int = Field(default=2, alias="GEMINI_MAX_CALLS_PER_ACTION")
    gemini_model_candidates: str = Field(default="", alias="GEMINI_MODEL_CANDIDATES")
    gemini_verify_limit: int = Field(default=3, alias="GEMINI_VERIFY_LIMIT")
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

    @field_validator("gemini_api_key")
    @classmethod
    def blank_key_is_missing(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("gemini_max_output_tokens")
    @classmethod
    def limit_output_tokens(cls, value: int) -> int:
        if value < 16 or value > 1024:
            raise ValueError("GEMINI_MAX_OUTPUT_TOKENS must be between 16 and 1024.")
        return value

    @field_validator("gemini_max_retries")
    @classmethod
    def limit_retries(cls, value: int) -> int:
        if value < 0 or value > 1:
            raise ValueError("GEMINI_MAX_RETRIES must be 0 or 1.")
        return value


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
