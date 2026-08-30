from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "NovaScale API"
    app_env: Literal[
        "local",
        "test",
        "staging",
        "production",
    ] = "local"

    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    database_url: str = (
        "postgresql+asyncpg://novascale:novascale_local_change_me@localhost:5432/novascale"
    )

    db_pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
    )

    db_max_overflow: int = Field(
        default=20,
        ge=0,
        le=100,
    )

    db_pool_timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
    )

    db_pool_recycle_seconds: int = Field(
        default=1800,
        ge=60,
    )

    auth_jwt_secret: str
    auth_jwt_algorithm: Literal["HS256"] = "HS256"

    access_token_ttl_minutes: int = Field(
        default=15,
        ge=1,
        le=60,
    )

    refresh_token_ttl_days: int = Field(
        default=30,
        ge=1,
        le=90,
    )

    jwt_issuer: str = "novascale"
    jwt_audience: str = "novascale-api"

    outbox_worker_poll_interval_seconds: float = Field(
        default=2.0,
        gt=0,
        le=60,
    )

    outbox_worker_batch_size: int = Field(
        default=50,
        ge=1,
        le=500,
    )

    outbox_worker_max_attempts: int = Field(
        default=5,
        ge=1,
        le=100,
    )

    outbox_worker_retry_base_seconds: float = Field(
        default=30.0,
        gt=0,
        le=3600,
    )

    outbox_worker_retry_max_seconds: float = Field(
        default=900.0,
        gt=0,
        le=86400,
    )

    outbox_worker_lease_seconds: float = Field(
        default=300.0,
        gt=0,
        le=3600,
    )

    notification_worker_poll_interval_seconds: float = Field(
        default=2.0,
        gt=0,
        le=60,
    )

    notification_worker_batch_size: int = Field(
        default=50,
        ge=1,
        le=500,
    )

    notification_worker_max_attempts: int = Field(
        default=3,
        ge=1,
        le=100,
    )

    notification_worker_retry_base_seconds: float = Field(
        default=30.0,
        gt=0,
        le=3600,
    )

    notification_worker_retry_max_seconds: float = Field(
        default=900.0,
        gt=0,
        le=86400,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings.model_validate({})
