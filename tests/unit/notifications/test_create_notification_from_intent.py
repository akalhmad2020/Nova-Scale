from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid4

from app.modules.notifications.application.contracts import (
    NotificationIntent,
)
from app.modules.notifications.application.ports.repositories import (
    NotificationAttemptRepository,
    NotificationRepository,
)
from app.modules.notifications.application.use_cases.create_notification import (
    CreateNotificationUseCase,
)
from app.modules.notifications.application.use_cases.create_notification_from_intent import (
    CreateNotificationFromIntentUseCase,
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

    async def add(self, notification: Notification) -> None:
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


async def test_create_notification_from_email_intent() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    create_notification = CreateNotificationUseCase(unit_of_work)

    use_case = CreateNotificationFromIntentUseCase(
        create_notification,
    )

    tenant_id = uuid4()

    intent = NotificationIntent(
        event_type="invoice.issued",
        recipient="billing@example.com",
        channel=NotificationChannel.EMAIL,
        subject="Invoice issued",
        body="Your invoice has been issued.",
        idempotency_key="invoice-issued-123",
    )

    notification = await use_case.execute(
        tenant_id=tenant_id,
        intent=intent,
    )

    assert notification.tenant_id == tenant_id
    assert notification.event_type == "invoice.issued"
    assert notification.recipient == "billing@example.com"
    assert notification.channel == NotificationChannel.EMAIL.value
    assert notification.subject == "Invoice issued"
    assert notification.body == "Your invoice has been issued."
    assert notification.idempotency_key == "invoice-issued-123"
    assert notification.status == NotificationStatus.PENDING.value

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


async def test_create_notification_from_webhook_intent() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    create_notification = CreateNotificationUseCase(unit_of_work)

    use_case = CreateNotificationFromIntentUseCase(
        create_notification,
    )

    tenant_id = uuid4()

    intent = NotificationIntent(
        event_type="shipment.updated",
        recipient="https://example.com/webhooks/novascale",
        channel=NotificationChannel.WEBHOOK,
        subject=None,
        body="Shipment updated.",
        idempotency_key="shipment-updated-123",
    )

    notification = await use_case.execute(
        tenant_id=tenant_id,
        intent=intent,
    )

    assert notification.tenant_id == tenant_id
    assert notification.channel == NotificationChannel.WEBHOOK.value
    assert notification.recipient == "https://example.com/webhooks/novascale"
    assert notification.subject is None
    assert notification.body == "Shipment updated."

    assert unit_of_work.commit_count == 1


async def test_notification_intent_preserves_idempotency() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    create_notification = CreateNotificationUseCase(unit_of_work)

    use_case = CreateNotificationFromIntentUseCase(
        create_notification,
    )

    tenant_id = uuid4()

    intent = NotificationIntent(
        event_type="invoice.issued",
        recipient="billing@example.com",
        channel=NotificationChannel.EMAIL,
        subject="Invoice issued",
        body="Your invoice has been issued.",
        idempotency_key="invoice-issued-456",
    )

    first = await use_case.execute(
        tenant_id=tenant_id,
        intent=intent,
    )

    second = await use_case.execute(
        tenant_id=tenant_id,
        intent=intent,
    )

    assert first is second
    assert first.idempotency_key == "invoice-issued-456"
    assert unit_of_work.commit_count == 1
