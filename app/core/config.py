from functools import lru_cache
from typing import Literal
from urllib.parse import unquote, urlsplit

from pydantic import Field, model_validator
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

    docs_enabled: bool = True

    allowed_hosts: list[str] = Field(
        default_factory=lambda: [
            "localhost",
            "127.0.0.1",
            "testserver",
        ]
    )

    cors_allowed_origins: list[str] = Field(
        default_factory=list,
    )

    hsts_enabled: bool = False

    billing_provider: Literal[
        "portfolio",
        "stripe",
    ] = "portfolio"

    database_url: str = (
        "postgresql+asyncpg://novascale_app:novascale_app_local_change_me@localhost:5432/novascale"
    )

    migration_database_url: str = (
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
    db_connect_timeout_seconds: int = Field(
        default=10,
        ge=1,
        le=60,
    )
    db_command_timeout_seconds: int = Field(
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

    login_max_failed_attempts: int = Field(
        default=5,
        ge=1,
        le=20,
    )
    login_lockout_minutes: int = Field(
        default=15,
        ge=1,
        le=1440,
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

    notification_smtp_host: str | None = None
    notification_smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
    )
    notification_smtp_username: str | None = None
    notification_smtp_password: str | None = None
    notification_smtp_from_address: str | None = None
    notification_smtp_starttls: bool = True
    notification_provider_timeout_seconds: float = Field(
        default=15.0,
        ge=1.0,
        le=120.0,
    )
    notification_webhook_allowed_hosts: list[str] = Field(
        default_factory=list,
    )

    ai_llm_provider: Literal["ollama"] = "ollama"
    ai_ollama_base_url: str = "http://host.docker.internal:11434"
    ai_ollama_model: str = "qwen2.5:3b"
    ai_ollama_timeout_seconds: float = Field(
        default=180.0,
        ge=1.0,
        le=600.0,
    )
    ai_ollama_max_attempts: int = Field(
        default=2,
        ge=1,
        le=4,
    )
    ai_ollama_retry_backoff_seconds: float = Field(
        default=0.25,
        ge=0.0,
        le=5.0,
    )
    ai_max_prompt_characters: int = Field(
        default=32_000,
        ge=1_000,
        le=200_000,
    )
    ai_max_system_prompt_characters: int = Field(
        default=16_000,
        ge=1_000,
        le=100_000,
    )
    ai_max_response_characters: int = Field(
        default=32_000,
        ge=1_000,
        le=200_000,
    )
    ai_max_output_tokens: int = Field(
        default=2_048,
        ge=64,
        le=16_384,
    )
    ai_max_context_window: int = Field(
        default=8_192,
        ge=512,
        le=131_072,
    )

    ai_embedding_provider: Literal["ollama"] = "ollama"
    ai_ollama_embedding_model: str = "nomic-embed-text"
    ai_document_storage_root: str = "./storage"

    @model_validator(mode="after")
    def validate_production_settings(
        self,
    ) -> "Settings":
        if self.app_env != "production":
            return self

        if self.debug:
            raise ValueError("DEBUG must be disabled in production.")

        if self.docs_enabled:
            raise ValueError("DOCS_ENABLED must be disabled in production.")

        if not self.allowed_hosts:
            raise ValueError("ALLOWED_HOSTS must contain at least one host in production.")

        if "*" in self.allowed_hosts:
            raise ValueError("ALLOWED_HOSTS must not contain '*' in production.")

        if not self.hsts_enabled:
            raise ValueError("HSTS_ENABLED must be enabled in production.")

        if len(self.auth_jwt_secret) < 32:
            raise ValueError("AUTH_JWT_SECRET must contain at least 32 characters in production.")

        unsafe_jwt_secrets = {
            "replace_with_a_strong_random_secret",
            "novascale_local_change_me",
        }

        if self.auth_jwt_secret in unsafe_jwt_secrets:
            raise ValueError("AUTH_JWT_SECRET must not use a placeholder value in production.")

        self._validate_production_database_url(
            setting_name="DATABASE_URL",
            value=self.database_url,
        )

        self._validate_production_database_url(
            setting_name="MIGRATION_DATABASE_URL",
            value=self.migration_database_url,
        )

        return self

    @staticmethod
    def _validate_production_database_url(
        *,
        setting_name: str,
        value: str,
    ) -> None:
        try:
            parsed = urlsplit(value)
        except ValueError as exc:
            raise ValueError(
                f"{setting_name} must be a valid PostgreSQL URL in production."
            ) from exc

        if not parsed.scheme.startswith("postgresql"):
            raise ValueError(f"{setting_name} must use PostgreSQL in production.")

        if not parsed.hostname:
            raise ValueError(f"{setting_name} must contain a database host in production.")

        if not parsed.username:
            raise ValueError(f"{setting_name} must contain a database username in production.")

        password = unquote(parsed.password) if parsed.password is not None else ""

        if not password:
            raise ValueError(f"{setting_name} must contain a database password in production.")

        unsafe_passwords = {
            "novascale_local_change_me",
            "novascale_app_local_change_me",
            "change_me",
            "changeme",
            "password",
        }

        normalized_password = password.strip().lower()

        if normalized_password in unsafe_passwords or "change_me" in normalized_password:
            raise ValueError(
                f"{setting_name} must not use development "
                "or placeholder database credentials "
                "in production."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings.model_validate({})
