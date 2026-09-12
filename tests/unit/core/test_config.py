import pytest
from pydantic import ValidationError

from app.core.config import Settings

SAFE_JWT_SECRET = "a-strong-production-secret-with-more-than-32-characters"

SAFE_DATABASE_URL = (
    "postgresql+asyncpg://novascale_app:runtime-production-password-7f3c9e@db:5432/novascale"
)

SAFE_MIGRATION_DATABASE_URL = (
    "postgresql+asyncpg://novascale_migrator:migration-production-password-4b8d2a@db:5432/novascale"
)


def production_settings(
    *,
    docs_enabled: bool = False,
    allowed_hosts: list[str] | None = None,
    hsts_enabled: bool = True,
    auth_jwt_secret: str = SAFE_JWT_SECRET,
    database_url: str = SAFE_DATABASE_URL,
    migration_database_url: str = SAFE_MIGRATION_DATABASE_URL,
) -> Settings:
    if allowed_hosts is None:
        allowed_hosts = [
            "api.novascale.example",
        ]

    return Settings(
        docs_enabled=docs_enabled,
        allowed_hosts=allowed_hosts,
        hsts_enabled=hsts_enabled,
        auth_jwt_secret=auth_jwt_secret,
        database_url=database_url,
        migration_database_url=migration_database_url,
    )


def test_production_rejects_debug_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "true",
    )

    with pytest.raises(
        ValidationError,
        match="DEBUG must be disabled in production",
    ):
        production_settings()


def test_production_rejects_docs_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match="DOCS_ENABLED must be disabled in production",
    ):
        production_settings(
            docs_enabled=True,
        )


def test_production_rejects_empty_allowed_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match=("ALLOWED_HOSTS must contain at least one host in production"),
    ):
        production_settings(
            allowed_hosts=[],
        )


def test_production_rejects_wildcard_allowed_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match="ALLOWED_HOSTS must not contain",
    ):
        production_settings(
            allowed_hosts=["*"],
        )


def test_production_rejects_hsts_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match="HSTS_ENABLED must be enabled in production",
    ):
        production_settings(
            hsts_enabled=False,
        )


def test_production_rejects_short_jwt_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match=("AUTH_JWT_SECRET must contain at least 32 characters in production"),
    ):
        production_settings(
            auth_jwt_secret="short",
        )


def test_production_rejects_placeholder_jwt_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match=("AUTH_JWT_SECRET must not use a placeholder value in production"),
    ):
        production_settings(
            auth_jwt_secret=("replace_with_a_strong_random_secret"),
        )


def test_production_rejects_runtime_database_placeholder_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match=(
            "DATABASE_URL must not use development or "
            "placeholder database credentials in production"
        ),
    ):
        production_settings(
            database_url=(
                "postgresql+asyncpg://novascale_app:novascale_app_local_change_me@db:5432/novascale"
            ),
        )


def test_production_rejects_migration_database_placeholder_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match=(
            "MIGRATION_DATABASE_URL must not use development "
            "or placeholder database credentials in production"
        ),
    ):
        production_settings(
            migration_database_url=(
                "postgresql+asyncpg://novascale:novascale_local_change_me@db:5432/novascale"
            ),
        )


def test_production_rejects_database_url_without_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match=("DATABASE_URL must contain a database password in production"),
    ):
        production_settings(
            database_url=("postgresql+asyncpg://novascale_app@db:5432/novascale"),
        )


def test_production_rejects_migration_database_url_without_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match=("MIGRATION_DATABASE_URL must contain a database password in production"),
    ):
        production_settings(
            migration_database_url=("postgresql+asyncpg://novascale_migrator@db:5432/novascale"),
        )


def test_production_rejects_non_postgresql_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match="DATABASE_URL must use PostgreSQL in production",
    ):
        production_settings(
            database_url="sqlite:///novascale.db",
        )


def test_production_rejects_database_url_without_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match=("DATABASE_URL must contain a database host in production"),
    ):
        production_settings(
            database_url=("postgresql+asyncpg://novascale_app:production-password@/novascale"),
        )


def test_production_rejects_database_url_without_username(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match=("DATABASE_URL must contain a database username in production"),
    ):
        production_settings(
            database_url=("postgresql+asyncpg://:production-password@db:5432/novascale"),
        )


def test_production_accepts_safe_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    settings = production_settings()

    assert settings.app_env == "production"
    assert settings.debug is False
    assert settings.docs_enabled is False
    assert settings.allowed_hosts == [
        "api.novascale.example",
    ]
    assert settings.hsts_enabled is True
    assert settings.auth_jwt_secret == SAFE_JWT_SECRET
    assert settings.database_url == SAFE_DATABASE_URL
    assert settings.migration_database_url == SAFE_MIGRATION_DATABASE_URL


def test_local_environment_allows_development_database_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "local",
    )
    monkeypatch.setenv(
        "DEBUG",
        "false",
    )

    settings = Settings(
        auth_jwt_secret="local-development-secret",
        database_url=(
            "postgresql+asyncpg://novascale_app:"
            "novascale_app_local_change_me"
            "@localhost:5432/novascale"
        ),
        migration_database_url=(
            "postgresql+asyncpg://novascale:novascale_local_change_me@localhost:5432/novascale"
        ),
    )

    assert settings.app_env == "local"
    assert "novascale_app_local_change_me" in settings.database_url
    assert "novascale_local_change_me" in settings.migration_database_url
