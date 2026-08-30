import pytest

from app.modules.notifications.application.exceptions import (
    NotificationProviderNotConfiguredError,
)
from app.modules.notifications.application.ports.providers import (
    NotificationDeliveryRequest,
    NotificationDeliveryResult,
)
from app.modules.notifications.domain.enums import NotificationChannel
from app.modules.notifications.infrastructure.providers.registry import (
    NotificationProviderRegistry,
)


class FakeEmailProvider:
    async def send(
        self,
        request: NotificationDeliveryRequest,
    ) -> NotificationDeliveryResult:
        return NotificationDeliveryResult(
            provider="fake-email",
            provider_message_id="email-message-123",
        )


class FakeWebhookProvider:
    async def send(
        self,
        request: NotificationDeliveryRequest,
    ) -> NotificationDeliveryResult:
        return NotificationDeliveryResult(
            provider="fake-webhook",
            provider_message_id="webhook-message-123",
        )


def test_resolve_email_provider() -> None:
    email_provider = FakeEmailProvider()
    webhook_provider = FakeWebhookProvider()

    registry = NotificationProviderRegistry(
        {
            NotificationChannel.EMAIL: email_provider,
            NotificationChannel.WEBHOOK: webhook_provider,
        }
    )

    resolved = registry.resolve(NotificationChannel.EMAIL)

    assert resolved is email_provider


def test_resolve_webhook_provider() -> None:
    email_provider = FakeEmailProvider()
    webhook_provider = FakeWebhookProvider()

    registry = NotificationProviderRegistry(
        {
            NotificationChannel.EMAIL: email_provider,
            NotificationChannel.WEBHOOK: webhook_provider,
        }
    )

    resolved = registry.resolve(NotificationChannel.WEBHOOK)

    assert resolved is webhook_provider


def test_missing_provider_raises_error() -> None:
    registry = NotificationProviderRegistry(
        {
            NotificationChannel.EMAIL: FakeEmailProvider(),
        }
    )

    with pytest.raises(
        NotificationProviderNotConfiguredError,
        match="webhook",
    ):
        registry.resolve(NotificationChannel.WEBHOOK)
