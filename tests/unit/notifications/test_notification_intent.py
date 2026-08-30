from datetime import UTC, datetime

from app.modules.notifications.application.contracts import (
    NotificationIntent,
)
from app.modules.notifications.domain.enums import NotificationChannel


def test_email_notification_intent() -> None:
    scheduled_at = datetime.now(UTC)

    intent = NotificationIntent(
        event_type="invoice.issued",
        recipient="billing@example.com",
        channel=NotificationChannel.EMAIL,
        subject="Invoice issued",
        body="Your invoice has been issued.",
        idempotency_key="invoice-issued-123",
        scheduled_at=scheduled_at,
    )

    assert intent.event_type == "invoice.issued"
    assert intent.recipient == "billing@example.com"
    assert intent.channel == NotificationChannel.EMAIL
    assert intent.subject == "Invoice issued"
    assert intent.body == "Your invoice has been issued."
    assert intent.idempotency_key == "invoice-issued-123"
    assert intent.scheduled_at == scheduled_at


def test_webhook_notification_intent() -> None:
    intent = NotificationIntent(
        event_type="shipment.updated",
        recipient="https://example.com/webhooks/novascale",
        channel=NotificationChannel.WEBHOOK,
        subject=None,
        body="Shipment updated.",
        idempotency_key="shipment-updated-123",
    )

    assert intent.channel == NotificationChannel.WEBHOOK
    assert intent.subject is None
    assert intent.scheduled_at is None
