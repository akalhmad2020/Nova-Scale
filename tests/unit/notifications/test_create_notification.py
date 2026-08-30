from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from app.modules.notifications.application.exceptions import (
    NotificationIdempotencyConflictError,
)
from app.modules.notifications.application.ports.repositories import (
    NotificationAttemptRepository,
    NotificationRepository,
)
from app.modules.notifications.application.use_cases.create_notification import (
    CreateNotificationUseCase,
)
from app.modules.notifications.domain.enums import (
    NotificationChannel,
    NotificationStatus,
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
        self.fail_on_add = False
        self.raise_idempotency_conflict_on_add = False
        self.existing_after_conflict: Notification | None = None

    async def add(self, notification: Notification) -> None:
        if self.fail_on_add:
            raise RuntimeError("notification repository failure")

        if self.raise_idempotency_conflict_on_add:
            if self.existing_after_conflict is not None:
                self.items.append(self.existing_after_conflict)

            raise NotificationIdempotencyConflictError

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
    ) -> Sequence[Notification]:
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
    ) -> Sequence[Notification]:
        return [
            notification
            for notification in self.items
            if notification.status == NotificationStatus.PENDING.value
            and (notification.scheduled_at is None or notification.scheduled_at <= now)
        ][:limit]


class FakeNotificationAttemptRepository:
    async def add(self, attempt: NotificationAttempt) -> None:
        pass

    async def list_for_notification(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> Sequence[NotificationAttempt]:
        return []

    async def get_latest_attempt(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> NotificationAttempt | None:
        return None


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


async def test_create_notification_creates_pending_notification() -> None:
    unit_of_work = FakeNotificationUnitOfWork()
    use_case = CreateNotificationUseCase(unit_of_work)

    tenant_id = uuid4()

    notification = await use_case.execute(
        tenant_id=tenant_id,
        event_type="invoice.issued",
        recipient="billing@example.com",
        channel=NotificationChannel.EMAIL,
        subject="Invoice issued",
        body="Your invoice has been issued.",
        idempotency_key="invoice-issued-123",
    )

    assert notification.tenant_id == tenant_id
    assert notification.event_type == "invoice.issued"
    assert notification.recipient == "billing@example.com"
    assert notification.channel == NotificationChannel.EMAIL.value
    assert notification.subject == "Invoice issued"
    assert notification.body == "Your invoice has been issued."
    assert notification.status == NotificationStatus.PENDING.value
    assert notification.idempotency_key == "invoice-issued-123"
    assert notification.scheduled_at is None
    assert notification.sent_at is None
    assert notification.failed_at is None
    assert notification.failure_reason is None

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


async def test_create_notification_normalizes_input() -> None:
    unit_of_work = FakeNotificationUnitOfWork()
    use_case = CreateNotificationUseCase(unit_of_work)

    notification = await use_case.execute(
        tenant_id=uuid4(),
        event_type="  invoice.issued  ",
        recipient="  billing@example.com  ",
        channel=NotificationChannel.EMAIL,
        subject="  Invoice issued  ",
        body="  Your invoice has been issued.  ",
        idempotency_key="  invoice-issued-123  ",
    )

    assert notification.event_type == "invoice.issued"
    assert notification.recipient == "billing@example.com"
    assert notification.subject == "Invoice issued"
    assert notification.body == "Your invoice has been issued."
    assert notification.idempotency_key == "invoice-issued-123"


async def test_create_notification_converts_blank_subject_to_none() -> None:
    unit_of_work = FakeNotificationUnitOfWork()
    use_case = CreateNotificationUseCase(unit_of_work)

    notification = await use_case.execute(
        tenant_id=uuid4(),
        event_type="shipment.updated",
        recipient="https://example.com/webhooks/novascale",
        channel=NotificationChannel.WEBHOOK,
        subject="   ",
        body="Shipment updated.",
        idempotency_key="shipment-updated-123",
    )

    assert notification.subject is None


async def test_create_notification_returns_existing_for_same_key() -> None:
    unit_of_work = FakeNotificationUnitOfWork()
    use_case = CreateNotificationUseCase(unit_of_work)

    tenant_id = uuid4()

    first = await use_case.execute(
        tenant_id=tenant_id,
        event_type="invoice.issued",
        recipient="billing@example.com",
        channel=NotificationChannel.EMAIL,
        subject="Invoice issued",
        body="Your invoice has been issued.",
        idempotency_key="invoice-issued-123",
    )

    previous_commit_count = unit_of_work.commit_count

    second = await use_case.execute(
        tenant_id=tenant_id,
        event_type="invoice.issued",
        recipient="other@example.com",
        channel=NotificationChannel.EMAIL,
        subject="Different subject",
        body="Different body.",
        idempotency_key="invoice-issued-123",
    )

    assert second is first
    assert unit_of_work.commit_count == previous_commit_count
    assert unit_of_work.rollback_count == 0


async def test_create_notification_recovers_from_idempotency_race() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)

    tenant_id = uuid4()
    idempotency_key = "invoice-issued-race-123"

    existing = Notification(
        id=uuid4(),
        tenant_id=tenant_id,
        event_type="invoice.issued",
        recipient="billing@example.com",
        channel=NotificationChannel.EMAIL.value,
        subject="Invoice issued",
        body="Your invoice has been issued.",
        status=NotificationStatus.PENDING.value,
        idempotency_key=idempotency_key,
        scheduled_at=None,
        sent_at=None,
        failed_at=None,
        failure_reason=None,
    )

    repository.raise_idempotency_conflict_on_add = True
    repository.existing_after_conflict = existing

    use_case = CreateNotificationUseCase(unit_of_work)

    result = await use_case.execute(
        tenant_id=tenant_id,
        event_type="invoice.issued",
        recipient="billing@example.com",
        channel=NotificationChannel.EMAIL,
        subject="Invoice issued",
        body="Your invoice has been issued.",
        idempotency_key=idempotency_key,
    )

    assert result is existing
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


async def test_create_notification_reraises_conflict_if_existing_not_found() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)

    repository.raise_idempotency_conflict_on_add = True
    repository.existing_after_conflict = None

    use_case = CreateNotificationUseCase(unit_of_work)

    with pytest.raises(NotificationIdempotencyConflictError):
        await use_case.execute(
            tenant_id=uuid4(),
            event_type="invoice.issued",
            recipient="billing@example.com",
            channel=NotificationChannel.EMAIL,
            subject="Invoice issued",
            body="Your invoice has been issued.",
            idempotency_key="missing-after-conflict",
        )

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.parametrize(
    ("event_type", "body", "idempotency_key"),
    [
        ("", "Body", "key"),
        ("   ", "Body", "key"),
        ("event", "", "key"),
        ("event", "   ", "key"),
        ("event", "Body", ""),
        ("event", "Body", "   "),
    ],
)
async def test_create_notification_rejects_blank_required_fields(
    event_type: str,
    body: str,
    idempotency_key: str,
) -> None:
    unit_of_work = FakeNotificationUnitOfWork()
    use_case = CreateNotificationUseCase(unit_of_work)

    with pytest.raises(ValueError):
        await use_case.execute(
            tenant_id=uuid4(),
            event_type=event_type,
            recipient="billing@example.com",
            channel=NotificationChannel.EMAIL,
            subject=None,
            body=body,
            idempotency_key=idempotency_key,
        )

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 0


async def test_create_notification_rejects_invalid_recipient() -> None:
    unit_of_work = FakeNotificationUnitOfWork()
    use_case = CreateNotificationUseCase(unit_of_work)

    with pytest.raises(ValueError):
        await use_case.execute(
            tenant_id=uuid4(),
            event_type="invoice.issued",
            recipient="invalid-email",
            channel=NotificationChannel.EMAIL,
            subject=None,
            body="Body",
            idempotency_key="key",
        )

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 0


async def test_create_notification_rolls_back_on_repository_failure() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)

    repository.fail_on_add = True

    use_case = CreateNotificationUseCase(unit_of_work)

    with pytest.raises(
        RuntimeError,
        match="notification repository failure",
    ):
        await use_case.execute(
            tenant_id=uuid4(),
            event_type="invoice.issued",
            recipient="billing@example.com",
            channel=NotificationChannel.EMAIL,
            subject=None,
            body="Body",
            idempotency_key="key",
        )

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1
