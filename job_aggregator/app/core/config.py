"""Application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    environment: Literal["local", "test", "production"] = Field(
        default="local",
        validation_alias="JOB_AGGREGATOR_ENV",
    )
    log_level: str = Field(
        default="INFO",
        validation_alias="JOB_AGGREGATOR_LOG_LEVEL",
    )
    database_url: str = Field(
        default="sqlite:///./data/job_aggregator.db",
        validation_alias="JOB_AGGREGATOR_DATABASE_URL",
    )
    http_timeout_seconds: float = Field(
        default=20.0,
        validation_alias="JOB_AGGREGATOR_HTTP_TIMEOUT_SECONDS",
    )
    http_max_retries: int = Field(
        default=2,
        validation_alias="JOB_AGGREGATOR_HTTP_MAX_RETRIES",
    )
    http_backoff_seconds: float = Field(
        default=0.5,
        validation_alias="JOB_AGGREGATOR_HTTP_BACKOFF_SECONDS",
    )
    per_host_concurrency: int = Field(
        default=2,
        validation_alias="JOB_AGGREGATOR_PER_HOST_CONCURRENCY",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
