import pytest

from app.core.config import Settings
from app.modules.notifications.application.exceptions import (
    NotificationProviderNotConfiguredError,
)
from app.modules.notifications.domain.enums import NotificationChannel
from app.modules.notifications.infrastructure.providers.logging import (
    LoggingEmailNotificationProvider,
    LoggingWebhookNotificationProvider,
)
from app.modules.notifications.infrastructure.providers.runtime import (
    build_notification_provider_registry,
)
from app.modules.notifications.infrastructure.providers.smtp import (
    SMTPEmailNotificationProvider,
)
from app.modules.notifications.infrastructure.providers.webhook import (
    HTTPWebhookNotificationProvider,
)

TEST_JWT_SECRET = "test-secret-for-novascale-at-least-32-characters"


def make_settings(
    app_env: str,
    *,
    smtp_configured: bool = False,
) -> Settings:
    values: dict[str, object] = {
        "app_env": app_env,
        "auth_jwt_secret": TEST_JWT_SECRET,
    }

    if app_env == "production":
        values.update(
            {
                "docs_enabled": False,
                "allowed_hosts": ["api.novascale.example"],
                "hsts_enabled": True,
            }
        )

    if smtp_configured:
        values.update(
            {
                "notification_smtp_host": "smtp.example.com",
                "notification_smtp_from_address": "notifications@example.com",
                "notification_webhook_allowed_hosts": [
                    "hooks.example.com",
                ],
            }
        )

    return Settings.model_validate(values)


@pytest.mark.parametrize(
    "app_env",
    [
        "local",
        "test",
    ],
)
def test_runtime_provider_registry_uses_logging_providers_in_safe_environments(
    app_env: str,
) -> None:
    settings = make_settings(app_env)

    registry = build_notification_provider_registry(
        settings=settings,
    )

    assert isinstance(
        registry.resolve(NotificationChannel.EMAIL),
        LoggingEmailNotificationProvider,
    )
    assert isinstance(
        registry.resolve(NotificationChannel.WEBHOOK),
        LoggingWebhookNotificationProvider,
    )


@pytest.mark.parametrize(
    "app_env",
    [
        "staging",
        "production",
    ],
)
def test_runtime_provider_registry_requires_smtp_configuration_outside_safe_environments(
    app_env: str,
) -> None:
    settings = make_settings(app_env)

    with pytest.raises(
        RuntimeError,
        match="NOTIFICATION_SMTP_HOST is required",
    ):
        build_notification_provider_registry(
            settings=settings,
        )


@pytest.mark.parametrize(
    "app_env",
    [
        "staging",
        "production",
    ],
)
def test_runtime_provider_registry_uses_production_providers_when_configured(
    app_env: str,
) -> None:
    settings = make_settings(
        app_env,
        smtp_configured=True,
    )

    registry = build_notification_provider_registry(
        settings=settings,
    )

    assert isinstance(
        registry.resolve(NotificationChannel.EMAIL),
        SMTPEmailNotificationProvider,
    )
    assert isinstance(
        registry.resolve(NotificationChannel.WEBHOOK),
        HTTPWebhookNotificationProvider,
    )


def test_registry_still_rejects_unconfigured_channel() -> None:
    settings = make_settings("local")

    registry = build_notification_provider_registry(
        settings=settings,
    )

    registry._providers.pop(NotificationChannel.WEBHOOK)

    with pytest.raises(NotificationProviderNotConfiguredError):
        registry.resolve(NotificationChannel.WEBHOOK)
