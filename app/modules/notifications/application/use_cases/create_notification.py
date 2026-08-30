from datetime import datetime
from uuid import UUID

from app.modules.notifications.application.exceptions import (
    NotificationIdempotencyConflictError,
)
from app.modules.notifications.application.ports.unit_of_work import (
    NotificationUnitOfWork,
)
from app.modules.notifications.domain.enums import (
    NotificationChannel,
    NotificationStatus,
)
from app.modules.notifications.domain.rules import (
    validate_notification_recipient,
)
from app.modules.notifications.infrastructure.models.notification import (
    Notification,
)


class CreateNotificationUseCase:
    def __init__(
        self,
        unit_of_work: NotificationUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        tenant_id: UUID,
        event_type: str,
        recipient: str,
        channel: NotificationChannel,
        subject: str | None,
        body: str,
        idempotency_key: str,
        scheduled_at: datetime | None = None,
    ) -> Notification:
        normalized_event_type = event_type.strip()
        normalized_recipient = recipient.strip()
        normalized_subject = subject.strip() if subject is not None else None
        normalized_body = body.strip()
        normalized_idempotency_key = idempotency_key.strip()

        if not normalized_event_type:
            raise ValueError("Notification event type cannot be empty.")

        if not normalized_body:
            raise ValueError("Notification body cannot be empty.")

        if not normalized_idempotency_key:
            raise ValueError("Notification idempotency key cannot be empty.")

        validate_notification_recipient(
            channel=channel,
            recipient=normalized_recipient,
        )

        existing = await self._unit_of_work.notifications.get_by_idempotency_key(
            tenant_id=tenant_id,
            idempotency_key=normalized_idempotency_key,
        )

        if existing is not None:
            return existing

        notification = Notification(
            tenant_id=tenant_id,
            event_type=normalized_event_type,
            recipient=normalized_recipient,
            channel=channel.value,
            subject=normalized_subject or None,
            body=normalized_body,
            status=NotificationStatus.PENDING.value,
            idempotency_key=normalized_idempotency_key,
            scheduled_at=scheduled_at,
            sent_at=None,
            failed_at=None,
            failure_reason=None,
        )

        try:
            await self._unit_of_work.notifications.add(notification)
            await self._unit_of_work.commit()
        except NotificationIdempotencyConflictError:
            await self._unit_of_work.rollback()

            existing = await self._unit_of_work.notifications.get_by_idempotency_key(
                tenant_id=tenant_id,
                idempotency_key=normalized_idempotency_key,
            )

            if existing is None:
                raise

            return existing
        except Exception:
            await self._unit_of_work.rollback()
            raise

        return notification
