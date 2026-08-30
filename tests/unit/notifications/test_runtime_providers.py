import pytest

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
    registry = build_notification_provider_registry(
        app_env=app_env,
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
def test_runtime_provider_registry_rejects_logging_providers_outside_safe_environments(
    app_env: str,
) -> None:
    with pytest.raises(
        RuntimeError,
        match="Production notification providers are not configured",
    ):
        build_notification_provider_registry(
            app_env=app_env,
        )


def test_registry_still_rejects_unconfigured_channel() -> None:
    registry = build_notification_provider_registry(
        app_env="local",
    )

    registry._providers.pop(NotificationChannel.WEBHOOK)

    with pytest.raises(NotificationProviderNotConfiguredError):
        registry.resolve(NotificationChannel.WEBHOOK)
