from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.notifications.application.ports.providers import (
    NotificationDeliveryRequest,
    NotificationDeliveryResult,
    NotificationProvider,
)
from app.modules.notifications.application.services.delivery_processor import (
    NotificationDeliveryProcessor,
)
from app.modules.notifications.domain.enums import (
    NotificationAttemptStatus,
    NotificationChannel,
    NotificationStatus,
)
from app.modules.notifications.infrastructure.models.notification import (
    Notification,
)
from app.modules.notifications.infrastructure.providers.registry import (
    NotificationProviderRegistry,
)
from app.modules.notifications.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyNotificationAttemptRepository,
    SQLAlchemyNotificationRepository,
)

pytestmark = pytest.mark.integration


class SelectiveEmailProvider:
    def __init__(
        self,
        *,
        failing_recipient: str,
    ) -> None:
        self._failing_recipient = failing_recipient
        self.requests: list[NotificationDeliveryRequest] = []

    async def send(
        self,
        request: NotificationDeliveryRequest,
    ) -> NotificationDeliveryResult:
        self.requests.append(request)

        if request.recipient == self._failing_recipient:
            raise RuntimeError("provider unavailable")

        return NotificationDeliveryResult(
            provider="selective-email",
            provider_message_id=f"message-{request.idempotency_key}",
        )


async def test_processor_continues_after_one_notification_fails(
    db_session: AsyncSession,
) -> None:
    tenant_a_id = uuid4()
    tenant_b_id = uuid4()

    first_notification = Notification(
        tenant_id=tenant_a_id,
        event_type="invoice.issued",
        recipient="first@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="First",
        body="First notification.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
    )

    failing_notification = Notification(
        tenant_id=tenant_a_id,
        event_type="invoice.issued",
        recipient="failing@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Failing",
        body="Failing notification.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
    )

    third_notification = Notification(
        tenant_id=tenant_b_id,
        event_type="invoice.issued",
        recipient="third@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Third",
        body="Third notification.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
    )

    db_session.add_all(
        [
            first_notification,
            failing_notification,
            third_notification,
        ]
    )

    await db_session.commit()

    first_notification_id = first_notification.id
    failing_notification_id = failing_notification.id
    third_notification_id = third_notification.id

    provider = SelectiveEmailProvider(
        failing_recipient="failing@example.com",
    )

    providers: dict[
        NotificationChannel,
        NotificationProvider,
    ] = {
        NotificationChannel.EMAIL: provider,
    }

    registry = NotificationProviderRegistry(providers)

    session_factory = async_sessionmaker(
        bind=db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    processor = NotificationDeliveryProcessor(
        session_factory=session_factory,
        provider_resolver=registry,
        batch_size=100,
        max_attempts=3,
        retry_base_seconds=30.0,
        retry_max_seconds=900.0,
    )

    result = await processor.process_batch()

    assert result.discovered >= 3
    assert result.delivered >= 2
    assert result.retryable_failures >= 1
    assert result.unexpected_failures == 0

    await db_session.rollback()
    db_session.expire_all()

    notification_repository = SQLAlchemyNotificationRepository(
        db_session,
    )

    persisted_first = await notification_repository.get_by_id(
        tenant_id=tenant_a_id,
        notification_id=first_notification_id,
    )

    persisted_failing = await notification_repository.get_by_id(
        tenant_id=tenant_a_id,
        notification_id=failing_notification_id,
    )

    persisted_third = await notification_repository.get_by_id(
        tenant_id=tenant_b_id,
        notification_id=third_notification_id,
    )

    assert persisted_first is not None
    assert persisted_failing is not None
    assert persisted_third is not None

    assert persisted_first.status == NotificationStatus.SENT.value
    assert persisted_third.status == NotificationStatus.SENT.value

    assert persisted_failing.status == NotificationStatus.PENDING.value
    assert persisted_failing.scheduled_at is not None
    assert persisted_failing.sent_at is None
    assert persisted_failing.failed_at is None

    attempt_repository = SQLAlchemyNotificationAttemptRepository(
        db_session,
    )

    first_attempts = await attempt_repository.list_for_notification(
        tenant_id=tenant_a_id,
        notification_id=first_notification_id,
    )

    failing_attempts = await attempt_repository.list_for_notification(
        tenant_id=tenant_a_id,
        notification_id=failing_notification_id,
    )

    third_attempts = await attempt_repository.list_for_notification(
        tenant_id=tenant_b_id,
        notification_id=third_notification_id,
    )

    assert len(first_attempts) == 1
    assert len(failing_attempts) == 1
    assert len(third_attempts) == 1

    assert first_attempts[0].status == NotificationAttemptStatus.SUCCESS.value

    assert failing_attempts[0].status == NotificationAttemptStatus.FAILED.value
    assert failing_attempts[0].attempt_number == 1
    assert failing_attempts[0].error == "provider unavailable"

    assert third_attempts[0].status == NotificationAttemptStatus.SUCCESS.value

    processed_request_recipients = {
        request.recipient
        for request in provider.requests
        if request.recipient
        in {
            "first@example.com",
            "failing@example.com",
            "third@example.com",
        }
    }

    assert processed_request_recipients == {
        "first@example.com",
        "failing@example.com",
        "third@example.com",
    }
