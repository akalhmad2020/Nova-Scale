from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.modules.notifications.application.contracts import (
    NotificationIntent,
)
from app.modules.notifications.domain.enums import NotificationChannel
from app.modules.notifications.infrastructure.outbox.handler import (
    InvalidNotificationOutboxPayloadError,
    NotificationOutboxHandler,
)
from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)


class FakeCreateNotificationFromIntentUseCase:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, NotificationIntent]] = []

    async def execute(
        self,
        *,
        tenant_id: UUID,
        intent: NotificationIntent,
    ) -> object:
        self.calls.append(
            (
                tenant_id,
                intent,
            )
        )

        return object()


def make_message(
    *,
    payload: dict[str, object],
    event_type: str = "invoice.issued",
) -> OutboxMessage:
    return OutboxMessage(
        tenant_id=uuid4(),
        event_type=event_type,
        payload=payload,
        status=OutboxMessageStatus.PROCESSING.value,
        attempt_count=1,
        available_at=None,
        claim_token=uuid4(),
        lease_expires_at=datetime.now(UTC),
        processed_at=None,
        last_error=None,
    )


async def test_handler_creates_email_notification_intent() -> None:
    use_case = FakeCreateNotificationFromIntentUseCase()
    handler = NotificationOutboxHandler(use_case)

    message = make_message(
        payload={
            "recipient": " billing@example.com ",
            "channel": "email",
            "subject": " Invoice issued ",
            "body": " Your invoice is ready. ",
            "idempotency_key": " invoice-issued-123 ",
        },
    )

    await handler.handle(message)

    assert len(use_case.calls) == 1

    tenant_id, intent = use_case.calls[0]

    assert tenant_id == message.tenant_id
    assert intent.event_type == "invoice.issued"
    assert intent.recipient == "billing@example.com"
    assert intent.channel == NotificationChannel.EMAIL
    assert intent.subject == "Invoice issued"
    assert intent.body == "Your invoice is ready."
    assert intent.idempotency_key == "invoice-issued-123"
    assert intent.scheduled_at is None


async def test_handler_creates_webhook_notification_intent() -> None:
    use_case = FakeCreateNotificationFromIntentUseCase()
    handler = NotificationOutboxHandler(use_case)

    message = make_message(
        event_type="shipment.created",
        payload={
            "recipient": "https://example.com/webhooks/shipments",
            "channel": "webhook",
            "subject": None,
            "body": '{"shipment_id":"123"}',
            "idempotency_key": "shipment-created-123",
        },
    )

    await handler.handle(message)

    assert len(use_case.calls) == 1

    _, intent = use_case.calls[0]

    assert intent.event_type == "shipment.created"
    assert intent.channel == NotificationChannel.WEBHOOK
    assert intent.subject is None
    assert intent.recipient == "https://example.com/webhooks/shipments"


@pytest.mark.parametrize(
    "field",
    [
        "recipient",
        "channel",
        "body",
        "idempotency_key",
    ],
)
async def test_handler_rejects_missing_required_field(
    field: str,
) -> None:
    use_case = FakeCreateNotificationFromIntentUseCase()
    handler = NotificationOutboxHandler(use_case)

    payload: dict[str, object] = {
        "recipient": "billing@example.com",
        "channel": "email",
        "subject": "Invoice issued",
        "body": "Your invoice is ready.",
        "idempotency_key": "invoice-issued-123",
    }

    del payload[field]

    message = make_message(
        payload=payload,
    )

    with pytest.raises(
        InvalidNotificationOutboxPayloadError,
        match=field,
    ):
        await handler.handle(message)

    assert use_case.calls == []


async def test_handler_rejects_invalid_channel() -> None:
    use_case = FakeCreateNotificationFromIntentUseCase()
    handler = NotificationOutboxHandler(use_case)

    message = make_message(
        payload={
            "recipient": "billing@example.com",
            "channel": "sms",
            "subject": "Invoice issued",
            "body": "Your invoice is ready.",
            "idempotency_key": "invoice-issued-123",
        },
    )

    with pytest.raises(
        InvalidNotificationOutboxPayloadError,
        match="Invalid notification channel",
    ):
        await handler.handle(message)

    assert use_case.calls == []


async def test_handler_normalizes_blank_subject_to_none() -> None:
    use_case = FakeCreateNotificationFromIntentUseCase()
    handler = NotificationOutboxHandler(use_case)

    message = make_message(
        payload={
            "recipient": "billing@example.com",
            "channel": "email",
            "subject": "   ",
            "body": "Your invoice is ready.",
            "idempotency_key": "invoice-issued-123",
        },
    )

    await handler.handle(message)

    _, intent = use_case.calls[0]

    assert intent.subject is None
