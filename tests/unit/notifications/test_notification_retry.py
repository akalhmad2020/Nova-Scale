from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.modules.notifications.application.exceptions import (
    NotificationDeliveryError,
    NotificationNotReadyError,
)
from app.modules.notifications.application.ports.providers import (
    NotificationDeliveryRequest,
    NotificationDeliveryResult,
    NotificationProvider,
)
from app.modules.notifications.application.ports.repositories import (
    NotificationAttemptRepository,
    NotificationRepository,
)
from app.modules.notifications.application.use_cases.deliver_notification import (
    DeliverNotificationUseCase,
)
from app.modules.notifications.domain.enums import (
    NotificationAttemptStatus,
    NotificationChannel,
    NotificationStatus,
)
from app.modules.notifications.domain.rules import (
    get_notification_retry_delay_seconds,
)
from app.modules.notifications.infrastructure.models.notification import (
    Notification,
)
from app.modules.notifications.infrastructure.models.notification_attempt import (
    NotificationAttempt,
)


class FakeNotificationRepository:
    def __init__(self) -> None:
        self.items: list[Notification] = []

    async def add(
        self,
        notification: Notification,
    ) -> None:
        self.items.append(notification)

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> Notification | None:
        return next(
            (
                notification
                for notification in self.items
                if notification.tenant_id == tenant_id and notification.id == notification_id
            ),
            None,
        )

    async def get_by_id_for_update(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> Notification | None:
        return await self.get_by_id(
            tenant_id=tenant_id,
            notification_id=notification_id,
        )

    async def get_by_idempotency_key(
        self,
        *,
        tenant_id: UUID,
        idempotency_key: str,
    ) -> Notification | None:
        return next(
            (
                notification
                for notification in self.items
                if notification.tenant_id == tenant_id
                and notification.idempotency_key == idempotency_key
            ),
            None,
        )

    async def list_ready_for_delivery(
        self,
        *,
        tenant_id: UUID,
        now: datetime,
        limit: int = 100,
    ) -> list[Notification]:
        return [
            notification
            for notification in self.items
            if notification.tenant_id == tenant_id
            and notification.status == NotificationStatus.PENDING.value
            and (notification.scheduled_at is None or notification.scheduled_at <= now)
        ][:limit]

    async def list_ready_for_delivery_global(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[Notification]:
        return [
            notification
            for notification in self.items
            if notification.status == NotificationStatus.PENDING.value
            and (notification.scheduled_at is None or notification.scheduled_at <= now)
        ][:limit]


class FakeNotificationAttemptRepository:
    def __init__(self) -> None:
        self.items: list[NotificationAttempt] = []

    async def add(
        self,
        attempt: NotificationAttempt,
    ) -> None:
        self.items.append(attempt)

    async def list_for_notification(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> list[NotificationAttempt]:
        return [
            attempt
            for attempt in self.items
            if attempt.tenant_id == tenant_id and attempt.notification_id == notification_id
        ]

    async def get_latest_attempt(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> NotificationAttempt | None:
        attempts = await self.list_for_notification(
            tenant_id=tenant_id,
            notification_id=notification_id,
        )

        if not attempts:
            return None

        return max(
            attempts,
            key=lambda attempt: attempt.attempt_number,
        )


class FakeNotificationUnitOfWork:
    def __init__(self) -> None:
        self.notifications: NotificationRepository = FakeNotificationRepository()
        self.attempts: NotificationAttemptRepository = FakeNotificationAttemptRepository()

        self.commit_count = 0
        self.rollback_count = 0

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


class AlwaysFailingProvider:
    async def send(
        self,
        request: NotificationDeliveryRequest,
    ) -> NotificationDeliveryResult:
        raise RuntimeError("provider unavailable")


class ProviderResolver:
    def __init__(
        self,
        provider: NotificationProvider,
    ) -> None:
        self._provider = provider

    def resolve(
        self,
        channel: NotificationChannel,
    ) -> NotificationProvider:
        return self._provider


def make_notification() -> Notification:
    return Notification(
        id=uuid4(),
        tenant_id=uuid4(),
        event_type="invoice.issued",
        recipient="billing@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Invoice issued",
        body="Your invoice has been issued.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=str(uuid4()),
    )


def test_retry_delay_uses_exponential_backoff() -> None:
    assert (
        get_notification_retry_delay_seconds(
            attempt_number=1,
            base_seconds=30.0,
            max_seconds=900.0,
        )
        == 30.0
    )

    assert (
        get_notification_retry_delay_seconds(
            attempt_number=2,
            base_seconds=30.0,
            max_seconds=900.0,
        )
        == 60.0
    )

    assert (
        get_notification_retry_delay_seconds(
            attempt_number=3,
            base_seconds=30.0,
            max_seconds=900.0,
        )
        == 120.0
    )


def test_retry_delay_respects_maximum() -> None:
    assert (
        get_notification_retry_delay_seconds(
            attempt_number=10,
            base_seconds=30.0,
            max_seconds=900.0,
        )
        == 900.0
    )


async def test_retryable_failure_schedules_next_delivery() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)

    notification = make_notification()
    repository.items.append(notification)

    use_case = DeliverNotificationUseCase(
        unit_of_work=unit_of_work,
        provider_resolver=ProviderResolver(
            AlwaysFailingProvider(),
        ),
        max_attempts=3,
        retry_base_seconds=30.0,
        retry_max_seconds=900.0,
    )

    before = datetime.now(UTC)

    with pytest.raises(
        NotificationDeliveryError,
        match="provider unavailable",
    ):
        await use_case.execute(
            tenant_id=notification.tenant_id,
            notification_id=notification.id,
        )

    after = datetime.now(UTC)

    assert notification.status == NotificationStatus.PENDING.value
    assert notification.scheduled_at is not None

    delay_from_before = (notification.scheduled_at - before).total_seconds()

    delay_from_after = (notification.scheduled_at - after).total_seconds()

    assert delay_from_before >= 30.0
    assert delay_from_after <= 30.0

    assert notification.failed_at is None
    assert notification.failure_reason is None

    attempts = unit_of_work.attempts
    assert isinstance(
        attempts,
        FakeNotificationAttemptRepository,
    )

    assert len(attempts.items) == 1
    assert attempts.items[0].attempt_number == 1
    assert attempts.items[0].status == NotificationAttemptStatus.FAILED.value


async def test_scheduled_retry_cannot_run_early() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)

    notification = make_notification()
    repository.items.append(notification)

    use_case = DeliverNotificationUseCase(
        unit_of_work=unit_of_work,
        provider_resolver=ProviderResolver(
            AlwaysFailingProvider(),
        ),
        max_attempts=3,
        retry_base_seconds=30.0,
        retry_max_seconds=900.0,
    )

    with pytest.raises(NotificationDeliveryError):
        await use_case.execute(
            tenant_id=notification.tenant_id,
            notification_id=notification.id,
        )

    with pytest.raises(NotificationNotReadyError):
        await use_case.execute(
            tenant_id=notification.tenant_id,
            notification_id=notification.id,
        )

    attempts = unit_of_work.attempts
    assert isinstance(
        attempts,
        FakeNotificationAttemptRepository,
    )

    assert len(attempts.items) == 1
