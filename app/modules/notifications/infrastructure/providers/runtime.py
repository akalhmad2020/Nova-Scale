from __future__ import annotations

from app.core.config import Settings
from app.modules.notifications.application.ports.providers import NotificationProvider
from app.modules.notifications.domain.enums import NotificationChannel
from app.modules.notifications.infrastructure.providers.logging import (
    LoggingEmailNotificationProvider,
    LoggingWebhookNotificationProvider,
)
from app.modules.notifications.infrastructure.providers.registry import (
    NotificationProviderRegistry,
)
from app.modules.notifications.infrastructure.providers.smtp import SMTPEmailNotificationProvider
from app.modules.notifications.infrastructure.providers.webhook import (
    HTTPWebhookNotificationProvider,
)


def build_notification_provider_registry(
    *,
    settings: Settings,
) -> NotificationProviderRegistry:
    if settings.app_env in {"local", "test"}:
        providers: dict[NotificationChannel, NotificationProvider] = {
            NotificationChannel.EMAIL: LoggingEmailNotificationProvider(),
            NotificationChannel.WEBHOOK: LoggingWebhookNotificationProvider(),
        }
        return NotificationProviderRegistry(providers)

    smtp_host = _required(
        settings.notification_smtp_host,
        "NOTIFICATION_SMTP_HOST",
    )
    smtp_from = _required(
        settings.notification_smtp_from_address,
        "NOTIFICATION_SMTP_FROM_ADDRESS",
    )

    providers = {
        NotificationChannel.EMAIL: SMTPEmailNotificationProvider(
            host=smtp_host,
            port=settings.notification_smtp_port,
            from_address=smtp_from,
            username=settings.notification_smtp_username,
            password=settings.notification_smtp_password,
            starttls=settings.notification_smtp_starttls,
            timeout_seconds=settings.notification_provider_timeout_seconds,
        ),
        NotificationChannel.WEBHOOK: HTTPWebhookNotificationProvider(
            allowed_hosts=tuple(settings.notification_webhook_allowed_hosts),
            timeout_seconds=settings.notification_provider_timeout_seconds,
            require_https=True,
        ),
    }

    return NotificationProviderRegistry(providers)


def _required(value: str | None, setting_name: str) -> str:
    normalized = value.strip() if value else ""

    if not normalized:
        raise RuntimeError(f"{setting_name} is required for staging/production notifications.")

    return normalized
