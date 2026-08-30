from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
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
from app.modules.notifications.infrastructure.outbox.handler import (
    NotificationOutboxHandler,
)
from app.modules.notifications.infrastructure.unit_of_work import (
    SQLAlchemyNotificationUnitOfWork,
)
from app.shared.outbox.application.processing_service import (
    OutboxProcessingService,
)
from app.shared.outbox.application.retry_policy import OutboxRetryPolicy
from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.handlers.registry import (
    OutboxMessageHandlerRegistry,
)
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)
from app.shared.outbox.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyOutboxMessageRepository,
)
from app.shared.outbox.infrastructure.unit_of_work import (
    SQLAlchemyOutboxUnitOfWork,
)

pytestmark = pytest.mark.integration

EVENT_TYPE = "notification.requested"


class NotificationUseCaseAdapter:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def execute(
        self,
        *,
        tenant_id: UUID,
        intent: object,
    ) -> object:
        from app.modules.notifications.application.contracts import (
            NotificationIntent,
        )

        if not isinstance(intent, NotificationIntent):
            raise TypeError("Expected NotificationIntent.")

        async with self._session_factory() as session:
            unit_of_work = SQLAlchemyNotificationUnitOfWork(session)

            create_notification = CreateNotificationUseCase(
                unit_of_work,
            )

            create_from_intent = CreateNotificationFromIntentUseCase(
                create_notification,
            )

            return await create_from_intent.execute(
                tenant_id=tenant_id,
                intent=intent,
            )


async def clear_test_data(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(OutboxMessage),
        )
        await session.execute(
            delete(Notification),
        )
        await session.commit()


async def create_outbox_message(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    tenant_id: UUID,
    idempotency_key: str,
) -> UUID:
    async with session_factory() as session:
        repository = SQLAlchemyOutboxMessageRepository(session)

        message = OutboxMessage(
            tenant_id=tenant_id,
            event_type=EVENT_TYPE,
            payload={
                "recipient": "billing@example.com",
                "channel": NotificationChannel.EMAIL.value,
                "subject": "Invoice issued",
                "body": "Your invoice is ready.",
                "idempotency_key": idempotency_key,
            },
            status=OutboxMessageStatus.PENDING.value,
            attempt_count=0,
            available_at=None,
            claim_token=None,
            lease_expires_at=None,
            processed_at=None,
            last_error=None,
        )

        await repository.add(message)

        message_id = message.id

        await session.commit()

        return message_id


def build_processing_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> OutboxProcessingService:
    notification_use_case = NotificationUseCaseAdapter(
        session_factory,
    )

    notification_handler = NotificationOutboxHandler(
        notification_use_case,
    )

    registry = OutboxMessageHandlerRegistry(
        {
            EVENT_TYPE: notification_handler,
        }
    )

    return OutboxProcessingService(
        unit_of_work_factory=lambda: SQLAlchemyOutboxUnitOfWork(session_factory),
        handler_resolver=registry,
        retry_policy=OutboxRetryPolicy(
            max_attempts=3,
            base_delay=timedelta(seconds=30),
            max_delay=timedelta(minutes=5),
        ),
        lease_duration=timedelta(minutes=5),
        batch_size=10,
    )


async def test_outbox_processing_creates_notification(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await clear_test_data(session_factory)

    tenant_id = uuid4()
    idempotency_key = f"notification-requested-{uuid4()}"

    message_id = await create_outbox_message(
        session_factory,
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
    )

    service = build_processing_service(
        session_factory,
    )

    now = datetime.now(UTC)

    processed_count = await service.process_batch(
        now=now,
    )

    assert processed_count == 1

    async with session_factory() as session:
        outbox_repository = SQLAlchemyOutboxMessageRepository(
            session,
        )

        outbox_message = await outbox_repository.get_by_id(
            message_id=message_id,
        )

        assert outbox_message is not None
        assert outbox_message.status == OutboxMessageStatus.PROCESSED.value
        assert outbox_message.processed_at == now
        assert outbox_message.attempt_count == 1
        assert outbox_message.claim_token is None
        assert outbox_message.lease_expires_at is None
        assert outbox_message.last_error is None

        statement = select(Notification).where(
            Notification.tenant_id == tenant_id,
            Notification.idempotency_key == idempotency_key,
        )

        result = await session.execute(statement)
        notification = result.scalar_one_or_none()

        assert notification is not None
        assert notification.tenant_id == tenant_id
        assert notification.event_type == EVENT_TYPE
        assert notification.recipient == "billing@example.com"
        assert notification.channel == NotificationChannel.EMAIL.value
        assert notification.subject == "Invoice issued"
        assert notification.body == "Your invoice is ready."
        assert notification.status == NotificationStatus.PENDING.value
        assert notification.idempotency_key == idempotency_key
        assert notification.scheduled_at is None


async def test_duplicate_notification_idempotency_key_does_not_duplicate_notification(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await clear_test_data(session_factory)

    tenant_id = uuid4()
    idempotency_key = f"notification-requested-{uuid4()}"

    first_message_id = await create_outbox_message(
        session_factory,
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
    )

    service = build_processing_service(
        session_factory,
    )

    first_count = await service.process_batch(
        now=datetime.now(UTC),
    )

    assert first_count == 1

    second_message_id = await create_outbox_message(
        session_factory,
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
    )

    second_count = await service.process_batch(
        now=datetime.now(UTC) + timedelta(seconds=1),
    )

    assert second_count == 1

    async with session_factory() as session:
        statement = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.tenant_id == tenant_id,
                Notification.idempotency_key == idempotency_key,
            )
        )

        result = await session.execute(statement)

        assert result.scalar_one() == 1

        repository = SQLAlchemyOutboxMessageRepository(session)

        first_message = await repository.get_by_id(
            message_id=first_message_id,
        )
        second_message = await repository.get_by_id(
            message_id=second_message_id,
        )

        assert first_message is not None
        assert second_message is not None

        assert first_message.status == OutboxMessageStatus.PROCESSED.value
        assert second_message.status == OutboxMessageStatus.PROCESSED.value


async def test_same_idempotency_key_is_isolated_by_tenant(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await clear_test_data(session_factory)

    first_tenant_id = uuid4()
    second_tenant_id = uuid4()

    idempotency_key = f"notification-requested-{uuid4()}"

    await create_outbox_message(
        session_factory,
        tenant_id=first_tenant_id,
        idempotency_key=idempotency_key,
    )

    await create_outbox_message(
        session_factory,
        tenant_id=second_tenant_id,
        idempotency_key=idempotency_key,
    )

    service = build_processing_service(
        session_factory,
    )

    processed_count = await service.process_batch(
        now=datetime.now(UTC),
    )

    assert processed_count == 2

    async with session_factory() as session:
        statement = select(Notification).where(
            Notification.idempotency_key == idempotency_key,
        )

        result = await session.execute(statement)
        notifications = list(result.scalars().all())

        assert len(notifications) == 2

        tenant_ids = {notification.tenant_id for notification in notifications}

        assert tenant_ids == {
            first_tenant_id,
            second_tenant_id,
        }
