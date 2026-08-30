from typing import Protocol
from uuid import UUID

from app.modules.notifications.application.contracts import (
    NotificationIntent,
)
from app.modules.notifications.domain.enums import NotificationChannel
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)


class InvalidNotificationOutboxPayloadError(Exception):
    pass


class CreateNotificationFromIntent(Protocol):
    async def execute(
        self,
        *,
        tenant_id: UUID,
        intent: NotificationIntent,
    ) -> object: ...


class NotificationOutboxHandler:
    def __init__(
        self,
        create_notification: CreateNotificationFromIntent,
    ) -> None:
        self._create_notification = create_notification

    async def handle(
        self,
        message: OutboxMessage,
    ) -> None:
        intent = self._build_intent(
            message=message,
        )

        await self._create_notification.execute(
            tenant_id=message.tenant_id,
            intent=intent,
        )

    def _build_intent(
        self,
        *,
        message: OutboxMessage,
    ) -> NotificationIntent:
        payload = message.payload

        recipient = self._require_string(
            payload=payload,
            field="recipient",
        )
        channel_value = self._require_string(
            payload=payload,
            field="channel",
        )
        body = self._require_string(
            payload=payload,
            field="body",
        )
        idempotency_key = self._require_string(
            payload=payload,
            field="idempotency_key",
        )

        subject = self._optional_string(
            payload=payload,
            field="subject",
        )

        try:
            channel = NotificationChannel(channel_value)
        except ValueError as exc:
            raise InvalidNotificationOutboxPayloadError(
                f"Invalid notification channel: {channel_value}"
            ) from exc

        return NotificationIntent(
            event_type=message.event_type,
            recipient=recipient,
            channel=channel,
            subject=subject,
            body=body,
            idempotency_key=idempotency_key,
            scheduled_at=None,
        )

    def _require_string(
        self,
        *,
        payload: dict[str, object],
        field: str,
    ) -> str:
        value = payload.get(field)

        if not isinstance(value, str):
            raise InvalidNotificationOutboxPayloadError(
                f"Notification outbox payload field '{field}' must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise InvalidNotificationOutboxPayloadError(
                f"Notification outbox payload field '{field}' cannot be empty."
            )

        return normalized

    def _optional_string(
        self,
        *,
        payload: dict[str, object],
        field: str,
    ) -> str | None:
        value = payload.get(field)

        if value is None:
            return None

        if not isinstance(value, str):
            raise InvalidNotificationOutboxPayloadError(
                f"Notification outbox payload field '{field}' must be a string or null."
            )

        normalized = value.strip()

        if not normalized:
            return None

        return normalized
