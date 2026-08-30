from __future__ import annotations

from app.modules.notifications.application.ports.providers import (
    NotificationProvider,
)
from app.modules.notifications.domain.enums import NotificationChannel
from app.modules.notifications.infrastructure.providers.logging import (
    LoggingEmailNotificationProvider,
    LoggingWebhookNotificationProvider,
)
from app.modules.notifications.infrastructure.providers.registry import (
    NotificationProviderRegistry,
)


def build_notification_provider_registry(
    *,
    app_env: str,
) -> NotificationProviderRegistry:
    if app_env not in {"local", "test"}:
        raise RuntimeError(
            "Production notification providers are not configured. "
            "Logging notification providers may only be used in "
            "local or test environments."
        )

    providers: dict[
        NotificationChannel,
        NotificationProvider,
    ] = {
        NotificationChannel.EMAIL: LoggingEmailNotificationProvider(),
        NotificationChannel.WEBHOOK: LoggingWebhookNotificationProvider(),
    }

    return NotificationProviderRegistry(providers)
