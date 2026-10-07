import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env file."""

    APP_NAME: str = "Bulk Certificate Generator API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database connection string
    # Defaults to SQLite for local development; easily overridden with PostgreSQL URI
    DATABASE_URL: str = "sqlite:///./certificates.db"

    # Local filesystem storage path for generated PDF certificates
    GENERATED_FILES_DIR: str = "generated"

    # Sensible bulk limits to protect memory and runtime
    MAX_RECIPIENTS_PER_JOB: int = 1000

    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    return Settings()


# Default instance for convenient access across modules
settings = get_settings()
