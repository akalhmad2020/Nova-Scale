from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.application.exceptions import (
    NotificationDeliveryError,
)
from app.modules.notifications.application.ports.providers import (
    NotificationDeliveryRequest,
    NotificationDeliveryResult,
    NotificationProvider,
)
from app.modules.notifications.application.use_cases.deliver_notification import (
    DeliverNotificationUseCase,
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
from app.modules.notifications.infrastructure.unit_of_work import (
    SQLAlchemyNotificationUnitOfWork,
)

pytestmark = pytest.mark.integration


class FakeNotificationProvider:
    def __init__(
        self,
        *,
        name: str,
        should_fail: bool = False,
    ) -> None:
        self.name = name
        self.should_fail = should_fail
        self.requests: list[NotificationDeliveryRequest] = []

    async def send(
        self,
        request: NotificationDeliveryRequest,
    ) -> NotificationDeliveryResult:
        self.requests.append(request)

        if self.should_fail:
            raise RuntimeError("provider unavailable")

        return NotificationDeliveryResult(
            provider=self.name,
            provider_message_id=f"{self.name}-message-123",
        )


def make_provider_registry(
    *,
    email_should_fail: bool = False,
    webhook_should_fail: bool = False,
) -> tuple[
    NotificationProviderRegistry,
    FakeNotificationProvider,
    FakeNotificationProvider,
]:
    email_provider = FakeNotificationProvider(
        name="fake-email",
        should_fail=email_should_fail,
    )

    webhook_provider = FakeNotificationProvider(
        name="fake-webhook",
        should_fail=webhook_should_fail,
    )

    providers: dict[
        NotificationChannel,
        NotificationProvider,
    ] = {
        NotificationChannel.EMAIL: email_provider,
        NotificationChannel.WEBHOOK: webhook_provider,
    }

    registry = NotificationProviderRegistry(providers)

    return registry, email_provider, webhook_provider


async def create_notification(
    db_session: AsyncSession,
    *,
    channel: NotificationChannel = NotificationChannel.EMAIL,
    recipient: str | None = None,
) -> Notification:
    if recipient is None:
        if channel == NotificationChannel.EMAIL:
            recipient = "billing@example.com"
        else:
            recipient = "https://example.com/webhooks/novascale"

    notification = Notification(
        tenant_id=uuid4(),
        event_type="invoice.issued",
        recipient=recipient,
        channel=channel.value,
        subject="Invoice issued",
        body="Your invoice has been issued.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
    )

    db_session.add(notification)
    await db_session.commit()
    await db_session.refresh(notification)

    return notification


async def test_successful_email_delivery_is_persisted(
    db_session: AsyncSession,
) -> None:
    notification = await create_notification(db_session)

    registry, email_provider, webhook_provider = make_provider_registry()

    use_case = DeliverNotificationUseCase(
        unit_of_work=SQLAlchemyNotificationUnitOfWork(db_session),
        provider_resolver=registry,
        max_attempts=3,
    )

    await use_case.execute(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    notification_repository = SQLAlchemyNotificationRepository(
        db_session,
    )
    attempt_repository = SQLAlchemyNotificationAttemptRepository(
        db_session,
    )

    persisted = await notification_repository.get_by_id(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    attempts = await attempt_repository.list_for_notification(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    assert persisted is not None
    assert persisted.status == NotificationStatus.SENT.value
    assert persisted.sent_at is not None
    assert persisted.failed_at is None
    assert persisted.failure_reason is None
    assert persisted.scheduled_at is None

    assert len(attempts) == 1

    attempt = attempts[0]

    assert attempt.attempt_number == 1
    assert attempt.status == NotificationAttemptStatus.SUCCESS.value
    assert attempt.provider == "fake-email"
    assert attempt.provider_message_id == "fake-email-message-123"
    assert attempt.error is None

    assert len(email_provider.requests) == 1
    assert webhook_provider.requests == []

    request = email_provider.requests[0]

    assert request.channel == NotificationChannel.EMAIL
    assert request.recipient == "billing@example.com"


async def test_successful_webhook_delivery_uses_webhook_provider(
    db_session: AsyncSession,
) -> None:
    notification = await create_notification(
        db_session,
        channel=NotificationChannel.WEBHOOK,
        recipient="https://example.com/webhooks/novascale",
    )

    registry, email_provider, webhook_provider = make_provider_registry()

    use_case = DeliverNotificationUseCase(
        unit_of_work=SQLAlchemyNotificationUnitOfWork(db_session),
        provider_resolver=registry,
        max_attempts=3,
    )

    await use_case.execute(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    notification_repository = SQLAlchemyNotificationRepository(
        db_session,
    )
    attempt_repository = SQLAlchemyNotificationAttemptRepository(
        db_session,
    )

    persisted = await notification_repository.get_by_id(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    attempts = await attempt_repository.list_for_notification(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    assert persisted is not None
    assert persisted.status == NotificationStatus.SENT.value
    assert persisted.sent_at is not None
    assert persisted.scheduled_at is None

    assert len(attempts) == 1

    attempt = attempts[0]

    assert attempt.status == NotificationAttemptStatus.SUCCESS.value
    assert attempt.provider == "fake-webhook"
    assert attempt.provider_message_id == "fake-webhook-message-123"

    assert email_provider.requests == []
    assert len(webhook_provider.requests) == 1

    request = webhook_provider.requests[0]

    assert request.channel == NotificationChannel.WEBHOOK
    assert request.recipient == "https://example.com/webhooks/novascale"


async def test_retryable_failure_is_persisted_as_pending(
    db_session: AsyncSession,
) -> None:
    notification = await create_notification(db_session)

    registry, email_provider, _ = make_provider_registry(
        email_should_fail=True,
    )

    use_case = DeliverNotificationUseCase(
        unit_of_work=SQLAlchemyNotificationUnitOfWork(db_session),
        provider_resolver=registry,
        max_attempts=3,
    )

    before_attempt = datetime.now(UTC)

    with pytest.raises(
        NotificationDeliveryError,
        match="provider unavailable",
    ):
        await use_case.execute(
            tenant_id=notification.tenant_id,
            notification_id=notification.id,
        )

    notification_repository = SQLAlchemyNotificationRepository(
        db_session,
    )
    attempt_repository = SQLAlchemyNotificationAttemptRepository(
        db_session,
    )

    persisted = await notification_repository.get_by_id(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    attempts = await attempt_repository.list_for_notification(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    assert persisted is not None
    assert persisted.status == NotificationStatus.PENDING.value
    assert persisted.sent_at is None
    assert persisted.failed_at is None
    assert persisted.failure_reason is None
    assert persisted.scheduled_at is not None
    assert persisted.scheduled_at >= before_attempt + timedelta(
        seconds=30,
    )

    assert len(attempts) == 1

    attempt = attempts[0]

    assert attempt.attempt_number == 1
    assert attempt.status == NotificationAttemptStatus.FAILED.value
    assert attempt.error == "provider unavailable"

    assert len(email_provider.requests) == 1


async def test_final_failure_is_persisted_as_failed(
    db_session: AsyncSession,
) -> None:
    notification = await create_notification(db_session)

    registry, email_provider, _ = make_provider_registry(
        email_should_fail=True,
    )

    use_case = DeliverNotificationUseCase(
        unit_of_work=SQLAlchemyNotificationUnitOfWork(db_session),
        provider_resolver=registry,
        max_attempts=3,
        retry_base_seconds=30.0,
        retry_max_seconds=900.0,
    )

    notification_repository = SQLAlchemyNotificationRepository(
        db_session,
    )
    attempt_repository = SQLAlchemyNotificationAttemptRepository(
        db_session,
    )

    for attempt_number in range(1, 4):
        with pytest.raises(
            NotificationDeliveryError,
            match="provider unavailable",
        ):
            await use_case.execute(
                tenant_id=notification.tenant_id,
                notification_id=notification.id,
            )

        persisted = await notification_repository.get_by_id(
            tenant_id=notification.tenant_id,
            notification_id=notification.id,
        )

        assert persisted is not None

        if attempt_number < 3:
            assert persisted.status == NotificationStatus.PENDING.value
            assert persisted.scheduled_at is not None
            assert persisted.failed_at is None
            assert persisted.failure_reason is None

            persisted.scheduled_at = datetime.now(UTC) - timedelta(seconds=1)
            await db_session.commit()
        else:
            assert persisted.status == NotificationStatus.FAILED.value
            assert persisted.scheduled_at is None
            assert persisted.failed_at is not None
            assert persisted.failure_reason == "provider unavailable"

    attempts = await attempt_repository.list_for_notification(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    assert len(attempts) == 3

    assert [attempt.attempt_number for attempt in attempts] == [
        1,
        2,
        3,
    ]

    assert all(attempt.status == NotificationAttemptStatus.FAILED.value for attempt in attempts)

    assert len(email_provider.requests) == 3


async def test_list_ready_for_delivery_excludes_future_notifications(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid4()
    now = datetime.now(UTC)

    ready_without_schedule = Notification(
        tenant_id=tenant_id,
        event_type="invoice.issued",
        recipient="ready1@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Ready",
        body="Ready notification.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
        scheduled_at=None,
    )

    ready_from_past = Notification(
        tenant_id=tenant_id,
        event_type="invoice.issued",
        recipient="ready2@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Ready",
        body="Ready notification.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
        scheduled_at=now - timedelta(minutes=5),
    )

    future_notification = Notification(
        tenant_id=tenant_id,
        event_type="invoice.issued",
        recipient="future@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Future",
        body="Future notification.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
        scheduled_at=now + timedelta(hours=1),
    )

    sent_notification = Notification(
        tenant_id=tenant_id,
        event_type="invoice.issued",
        recipient="sent@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Sent",
        body="Already sent.",
        status=NotificationStatus.SENT.value,
        idempotency_key=str(uuid4()),
        scheduled_at=None,
    )

    db_session.add_all(
        [
            ready_without_schedule,
            ready_from_past,
            future_notification,
            sent_notification,
        ]
    )

    await db_session.commit()

    repository = SQLAlchemyNotificationRepository(
        db_session,
    )

    results = await repository.list_ready_for_delivery(
        tenant_id=tenant_id,
        now=now,
    )

    result_ids = {notification.id for notification in results}

    assert ready_without_schedule.id in result_ids
    assert ready_from_past.id in result_ids
    assert future_notification.id not in result_ids
    assert sent_notification.id not in result_ids


async def test_list_ready_for_delivery_is_tenant_isolated(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    now = datetime.now(UTC)

    tenant_notification = Notification(
        tenant_id=tenant_id,
        event_type="invoice.issued",
        recipient="tenant@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Tenant notification",
        body="Tenant notification.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
        scheduled_at=None,
    )

    other_tenant_notification = Notification(
        tenant_id=other_tenant_id,
        event_type="invoice.issued",
        recipient="other@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Other tenant notification",
        body="Other tenant notification.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
        scheduled_at=None,
    )

    db_session.add_all(
        [
            tenant_notification,
            other_tenant_notification,
        ]
    )

    await db_session.commit()

    repository = SQLAlchemyNotificationRepository(
        db_session,
    )

    results = await repository.list_ready_for_delivery(
        tenant_id=tenant_id,
        now=now,
    )

    result_ids = {notification.id for notification in results}

    assert tenant_notification.id in result_ids
    assert other_tenant_notification.id not in result_ids


async def test_list_ready_for_delivery_global_returns_due_notifications_across_tenants(
    db_session: AsyncSession,
) -> None:
    tenant_a_id = uuid4()
    tenant_b_id = uuid4()
    now = datetime.now(UTC)

    tenant_a_ready = Notification(
        tenant_id=tenant_a_id,
        event_type="invoice.issued",
        recipient="tenant-a@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Tenant A",
        body="Tenant A ready notification.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
        scheduled_at=None,
    )

    tenant_b_ready = Notification(
        tenant_id=tenant_b_id,
        event_type="invoice.issued",
        recipient="tenant-b@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Tenant B",
        body="Tenant B ready notification.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
        scheduled_at=now - timedelta(minutes=5),
    )

    tenant_a_future = Notification(
        tenant_id=tenant_a_id,
        event_type="invoice.issued",
        recipient="future@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Future",
        body="Future notification.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
        scheduled_at=now + timedelta(hours=1),
    )

    tenant_b_sent = Notification(
        tenant_id=tenant_b_id,
        event_type="invoice.issued",
        recipient="sent@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Sent",
        body="Already sent.",
        status=NotificationStatus.SENT.value,
        idempotency_key=str(uuid4()),
        scheduled_at=None,
        sent_at=now,
    )

    db_session.add_all(
        [
            tenant_a_ready,
            tenant_b_ready,
            tenant_a_future,
            tenant_b_sent,
        ]
    )

    await db_session.commit()

    repository = SQLAlchemyNotificationRepository(
        db_session,
    )

    results = await repository.list_ready_for_delivery_global(
        now=now,
        limit=100,
    )

    result_ids = {notification.id for notification in results}

    assert tenant_a_ready.id in result_ids
    assert tenant_b_ready.id in result_ids

    assert tenant_a_future.id not in result_ids
    assert tenant_b_sent.id not in result_ids

    returned_tenant_ids = {
        notification.tenant_id
        for notification in results
        if notification.id
        in {
            tenant_a_ready.id,
            tenant_b_ready.id,
        }
    }

    assert returned_tenant_ids == {
        tenant_a_id,
        tenant_b_id,
    }
