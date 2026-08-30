from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.modules.notifications.application.exceptions import (
    NotificationAlreadyProcessedError,
    NotificationDeliveryError,
    NotificationNotFoundError,
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
    def __init__(self) -> None:
        self.items: list[NotificationAttempt] = []
        self.fail_on_add = False

    async def add(self, attempt: NotificationAttempt) -> None:
        if self.fail_on_add:
            raise RuntimeError("attempt repository failure")

        self.items.append(attempt)

    async def list_for_notification(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> Sequence[NotificationAttempt]:
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


class FakeNotificationProviderResolver:
    def __init__(
        self,
        providers: dict[
            NotificationChannel,
            NotificationProvider,
        ],
    ) -> None:
        self.providers = providers
        self.resolved_channels: list[NotificationChannel] = []

    def resolve(
        self,
        channel: NotificationChannel,
    ) -> NotificationProvider:
        self.resolved_channels.append(channel)
        return self.providers[channel]


def make_notification(
    *,
    tenant_id: UUID | None = None,
    status: NotificationStatus = NotificationStatus.PENDING,
    channel: NotificationChannel = NotificationChannel.EMAIL,
    recipient: str | None = None,
) -> Notification:
    if recipient is None:
        if channel == NotificationChannel.EMAIL:
            recipient = "billing@example.com"
        else:
            recipient = "https://example.com/webhooks/novascale"

    return Notification(
        id=uuid4(),
        tenant_id=tenant_id or uuid4(),
        event_type="invoice.issued",
        recipient=recipient,
        channel=channel.value,
        subject="Invoice issued",
        body="Your invoice has been issued.",
        status=status.value,
        idempotency_key=str(uuid4()),
    )


def make_provider_resolver(
    *,
    email_should_fail: bool = False,
    webhook_should_fail: bool = False,
) -> tuple[
    FakeNotificationProviderResolver,
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

    resolver = FakeNotificationProviderResolver(
        {
            NotificationChannel.EMAIL: email_provider,
            NotificationChannel.WEBHOOK: webhook_provider,
        }
    )

    return resolver, email_provider, webhook_provider


async def test_deliver_email_notification_uses_email_provider() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    resolver, email_provider, webhook_provider = make_provider_resolver()

    notification = make_notification(
        channel=NotificationChannel.EMAIL,
    )

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)
    repository.items.append(notification)

    use_case = DeliverNotificationUseCase(
        unit_of_work=unit_of_work,
        provider_resolver=resolver,
        max_attempts=3,
    )

    result = await use_case.execute(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    assert result is notification
    assert notification.status == NotificationStatus.SENT.value

    assert resolver.resolved_channels == [
        NotificationChannel.EMAIL,
    ]

    assert len(email_provider.requests) == 1
    assert webhook_provider.requests == []

    request = email_provider.requests[0]

    assert request.channel == NotificationChannel.EMAIL
    assert request.recipient == "billing@example.com"


async def test_deliver_webhook_notification_uses_webhook_provider() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    resolver, email_provider, webhook_provider = make_provider_resolver()

    notification = make_notification(
        channel=NotificationChannel.WEBHOOK,
    )

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)
    repository.items.append(notification)

    use_case = DeliverNotificationUseCase(
        unit_of_work=unit_of_work,
        provider_resolver=resolver,
        max_attempts=3,
    )

    result = await use_case.execute(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    assert result is notification
    assert notification.status == NotificationStatus.SENT.value

    assert resolver.resolved_channels == [
        NotificationChannel.WEBHOOK,
    ]

    assert email_provider.requests == []
    assert len(webhook_provider.requests) == 1

    request = webhook_provider.requests[0]

    assert request.channel == NotificationChannel.WEBHOOK
    assert request.recipient == "https://example.com/webhooks/novascale"


async def test_successful_delivery_is_recorded() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    resolver, email_provider, _ = make_provider_resolver()

    notification = make_notification()

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)
    repository.items.append(notification)

    use_case = DeliverNotificationUseCase(
        unit_of_work=unit_of_work,
        provider_resolver=resolver,
        max_attempts=3,
    )

    result = await use_case.execute(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    assert result is notification
    assert notification.status == NotificationStatus.SENT.value
    assert notification.sent_at is not None
    assert notification.failed_at is None
    assert notification.failure_reason is None

    assert len(email_provider.requests) == 1

    attempts = unit_of_work.attempts
    assert isinstance(attempts, FakeNotificationAttemptRepository)
    assert len(attempts.items) == 1

    attempt = attempts.items[0]

    assert attempt.attempt_number == 1
    assert attempt.status == NotificationAttemptStatus.SUCCESS.value
    assert attempt.provider == "fake-email"
    assert attempt.provider_message_id == "fake-email-message-123"
    assert attempt.error is None

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


async def test_retryable_failure_remains_pending() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    resolver, email_provider, _ = make_provider_resolver(
        email_should_fail=True,
    )

    notification = make_notification()

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)
    repository.items.append(notification)

    use_case = DeliverNotificationUseCase(
        unit_of_work=unit_of_work,
        provider_resolver=resolver,
        max_attempts=3,
    )

    with pytest.raises(
        NotificationDeliveryError,
        match="provider unavailable",
    ):
        await use_case.execute(
            tenant_id=notification.tenant_id,
            notification_id=notification.id,
        )

    assert len(email_provider.requests) == 1

    assert notification.status == NotificationStatus.PENDING.value
    assert notification.sent_at is None
    assert notification.failed_at is None
    assert notification.failure_reason is None

    attempts = unit_of_work.attempts
    assert isinstance(attempts, FakeNotificationAttemptRepository)

    assert len(attempts.items) == 1

    attempt = attempts.items[0]

    assert attempt.attempt_number == 1
    assert attempt.status == NotificationAttemptStatus.FAILED.value
    assert attempt.error == "provider unavailable"

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


async def test_final_failed_delivery_marks_notification_failed() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    resolver, _, _ = make_provider_resolver(
        email_should_fail=True,
    )

    notification = make_notification()

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)
    repository.items.append(notification)

    attempts = unit_of_work.attempts
    assert isinstance(attempts, FakeNotificationAttemptRepository)

    now = datetime.now(UTC)

    attempts.items.extend(
        [
            NotificationAttempt(
                id=uuid4(),
                tenant_id=notification.tenant_id,
                notification_id=notification.id,
                attempt_number=1,
                status=NotificationAttemptStatus.FAILED.value,
                provider="fake-email",
                provider_message_id=None,
                error="first failure",
                attempted_at=now,
            ),
            NotificationAttempt(
                id=uuid4(),
                tenant_id=notification.tenant_id,
                notification_id=notification.id,
                attempt_number=2,
                status=NotificationAttemptStatus.FAILED.value,
                provider="fake-email",
                provider_message_id=None,
                error="second failure",
                attempted_at=now,
            ),
        ]
    )

    use_case = DeliverNotificationUseCase(
        unit_of_work=unit_of_work,
        provider_resolver=resolver,
        max_attempts=3,
    )

    with pytest.raises(NotificationDeliveryError):
        await use_case.execute(
            tenant_id=notification.tenant_id,
            notification_id=notification.id,
        )

    assert notification.status == NotificationStatus.FAILED.value
    assert notification.failed_at is not None
    assert notification.failure_reason == "provider unavailable"

    assert len(attempts.items) == 3

    final_attempt = attempts.items[-1]

    assert final_attempt.attempt_number == 3
    assert final_attempt.status == NotificationAttemptStatus.FAILED.value

    assert unit_of_work.commit_count == 1


@pytest.mark.parametrize(
    "status",
    [
        NotificationStatus.SENT,
        NotificationStatus.FAILED,
    ],
)
async def test_processed_notification_cannot_be_delivered_again(
    status: NotificationStatus,
) -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    resolver, email_provider, webhook_provider = make_provider_resolver()

    notification = make_notification(status=status)

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)
    repository.items.append(notification)

    use_case = DeliverNotificationUseCase(
        unit_of_work=unit_of_work,
        provider_resolver=resolver,
    )

    with pytest.raises(NotificationAlreadyProcessedError):
        await use_case.execute(
            tenant_id=notification.tenant_id,
            notification_id=notification.id,
        )

    attempts = unit_of_work.attempts
    assert isinstance(attempts, FakeNotificationAttemptRepository)

    assert resolver.resolved_channels == []
    assert email_provider.requests == []
    assert webhook_provider.requests == []
    assert attempts.items == []
    assert unit_of_work.commit_count == 0


async def test_missing_notification_raises_not_found() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    resolver, email_provider, webhook_provider = make_provider_resolver()

    use_case = DeliverNotificationUseCase(
        unit_of_work=unit_of_work,
        provider_resolver=resolver,
    )

    with pytest.raises(NotificationNotFoundError):
        await use_case.execute(
            tenant_id=uuid4(),
            notification_id=uuid4(),
        )

    attempts = unit_of_work.attempts
    assert isinstance(attempts, FakeNotificationAttemptRepository)

    assert resolver.resolved_channels == []
    assert email_provider.requests == []
    assert webhook_provider.requests == []
    assert attempts.items == []
    assert unit_of_work.commit_count == 0


async def test_delivery_uses_next_attempt_number() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    resolver, _, _ = make_provider_resolver()

    notification = make_notification()

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)
    repository.items.append(notification)

    attempts = unit_of_work.attempts
    assert isinstance(attempts, FakeNotificationAttemptRepository)

    previous_attempt = NotificationAttempt(
        id=uuid4(),
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
        attempt_number=1,
        status=NotificationAttemptStatus.FAILED.value,
        provider="fake-email",
        provider_message_id=None,
        error="temporary failure",
        attempted_at=datetime.now(UTC),
    )

    attempts.items.append(previous_attempt)

    use_case = DeliverNotificationUseCase(
        unit_of_work=unit_of_work,
        provider_resolver=resolver,
        max_attempts=3,
    )

    await use_case.execute(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
    )

    assert len(attempts.items) == 2

    latest_attempt = attempts.items[-1]

    assert latest_attempt.attempt_number == 2
    assert latest_attempt.status == NotificationAttemptStatus.SUCCESS.value
    assert notification.status == NotificationStatus.SENT.value


async def test_attempt_persistence_failure_rolls_back() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    attempts = unit_of_work.attempts
    assert isinstance(attempts, FakeNotificationAttemptRepository)
    attempts.fail_on_add = True

    resolver, _, _ = make_provider_resolver()

    notification = make_notification()

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)
    repository.items.append(notification)

    use_case = DeliverNotificationUseCase(
        unit_of_work=unit_of_work,
        provider_resolver=resolver,
    )

    with pytest.raises(
        RuntimeError,
        match="attempt repository failure",
    ):
        await use_case.execute(
            tenant_id=notification.tenant_id,
            notification_id=notification.id,
        )

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


async def test_future_scheduled_notification_cannot_be_delivered() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    resolver, email_provider, webhook_provider = make_provider_resolver()

    notification = make_notification()
    notification.scheduled_at = datetime.now(UTC) + timedelta(hours=1)

    repository = unit_of_work.notifications
    assert isinstance(repository, FakeNotificationRepository)
    repository.items.append(notification)

    use_case = DeliverNotificationUseCase(
        unit_of_work=unit_of_work,
        provider_resolver=resolver,
    )

    with pytest.raises(NotificationNotReadyError):
        await use_case.execute(
            tenant_id=notification.tenant_id,
            notification_id=notification.id,
        )

    attempts = unit_of_work.attempts
    assert isinstance(attempts, FakeNotificationAttemptRepository)

    assert notification.status == NotificationStatus.PENDING.value

    assert resolver.resolved_channels == []
    assert email_provider.requests == []
    assert webhook_provider.requests == []
    assert attempts.items == []
    assert unit_of_work.commit_count == 0


def test_deliver_notification_rejects_invalid_max_attempts() -> None:
    unit_of_work = FakeNotificationUnitOfWork()

    resolver, _, _ = make_provider_resolver()

    with pytest.raises(
        ValueError,
        match="Maximum attempts must be at least 1",
    ):
        DeliverNotificationUseCase(
            unit_of_work=unit_of_work,
            provider_resolver=resolver,
            max_attempts=0,
        )
