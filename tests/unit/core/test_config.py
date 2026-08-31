import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_debug_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "true")

    with pytest.raises(
        ValidationError,
        match="DEBUG must be disabled in production",
    ):
        Settings(
            docs_enabled=False,
            allowed_hosts=["api.novascale.example"],
            hsts_enabled=True,
            auth_jwt_secret="this-is-a-very-long-production-secret-value",
        )


def test_production_rejects_docs_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")

    with pytest.raises(
        ValidationError,
        match="DOCS_ENABLED must be disabled in production",
    ):
        Settings(
            docs_enabled=True,
            allowed_hosts=["api.novascale.example"],
            hsts_enabled=True,
            auth_jwt_secret=("a-strong-production-secret-with-more-than-32-characters"),
        )


def test_production_rejects_empty_allowed_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")

    with pytest.raises(
        ValidationError,
        match="ALLOWED_HOSTS must contain at least one host in production",
    ):
        Settings(
            docs_enabled=False,
            allowed_hosts=[],
            hsts_enabled=True,
            auth_jwt_secret=("a-strong-production-secret-with-more-than-32-characters"),
        )


def test_production_rejects_wildcard_allowed_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")

    with pytest.raises(
        ValidationError,
        match="ALLOWED_HOSTS must not contain",
    ):
        Settings(
            docs_enabled=False,
            allowed_hosts=["*"],
            hsts_enabled=True,
            auth_jwt_secret=("a-strong-production-secret-with-more-than-32-characters"),
        )


def test_production_rejects_hsts_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")

    with pytest.raises(
        ValidationError,
        match="HSTS_ENABLED must be enabled in production",
    ):
        Settings(
            docs_enabled=False,
            allowed_hosts=["api.novascale.example"],
            hsts_enabled=False,
            auth_jwt_secret=("a-strong-production-secret-with-more-than-32-characters"),
        )


def test_production_rejects_short_jwt_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")

    with pytest.raises(
        ValidationError,
        match="AUTH_JWT_SECRET must contain at least 32 characters in production",
    ):
        Settings(
            docs_enabled=False,
            allowed_hosts=["api.novascale.example"],
            hsts_enabled=True,
            auth_jwt_secret="short",
        )


def test_production_rejects_placeholder_jwt_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")

    with pytest.raises(
        ValidationError,
        match="AUTH_JWT_SECRET must not use a placeholder value in production",
    ):
        Settings(
            docs_enabled=False,
            allowed_hosts=["api.novascale.example"],
            hsts_enabled=True,
            auth_jwt_secret="replace_with_a_strong_random_secret",
        )


def test_production_accepts_safe_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")

    settings = Settings(
        docs_enabled=False,
        allowed_hosts=["api.novascale.example"],
        hsts_enabled=True,
        auth_jwt_secret=("a-strong-production-secret-with-more-than-32-characters"),
    )

    assert settings.app_env == "production"
    assert settings.debug is False
    assert settings.docs_enabled is False
    assert settings.allowed_hosts == ["api.novascale.example"]
    assert settings.hsts_enabled is True
