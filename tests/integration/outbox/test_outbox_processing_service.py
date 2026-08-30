from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.shared.outbox.application.processing_service import (
    OutboxProcessingService,
)
from app.shared.outbox.application.retry_policy import OutboxRetryPolicy
from app.shared.outbox.domain.enums import OutboxMessageStatus
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


class SuccessfulHandler:
    def __init__(self) -> None:
        self.handled_ids: list[UUID] = []

    async def handle(
        self,
        message: OutboxMessage,
    ) -> None:
        self.handled_ids.append(message.id)


class FailingHandler:
    def __init__(
        self,
        *,
        error: str,
    ) -> None:
        self.error = error
        self.calls = 0

    async def handle(
        self,
        message: OutboxMessage,
    ) -> None:
        self.calls += 1
        raise RuntimeError(self.error)


class HandlerResolver:
    def __init__(
        self,
        handler: SuccessfulHandler | FailingHandler,
    ) -> None:
        self._handler = handler

    def resolve(
        self,
        event_type: str,
    ) -> SuccessfulHandler | FailingHandler:
        return self._handler


async def clear_outbox(
    session: AsyncSession,
) -> None:
    await session.execute(
        delete(OutboxMessage),
    )
    await session.commit()


async def create_pending_message(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    attempt_count: int = 0,
) -> UUID:
    async with session_factory() as session:
        repository = SQLAlchemyOutboxMessageRepository(session)

        message = OutboxMessage(
            tenant_id=uuid4(),
            event_type=f"processing.service.{uuid4()}",
            payload={"type": "processing-service"},
            status=OutboxMessageStatus.PENDING.value,
            attempt_count=attempt_count,
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


async def test_processing_service_marks_successful_message_processed(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as cleanup_session:
        await clear_outbox(cleanup_session)

    message_id = await create_pending_message(session_factory)

    handler = SuccessfulHandler()
    resolver = HandlerResolver(handler)

    service = OutboxProcessingService(
        unit_of_work_factory=lambda: SQLAlchemyOutboxUnitOfWork(session_factory),
        handler_resolver=resolver,
        retry_policy=OutboxRetryPolicy(),
        lease_duration=timedelta(minutes=5),
        batch_size=10,
    )

    now = datetime.now(UTC)

    processed_count = await service.process_batch(
        now=now,
    )

    assert processed_count == 1
    assert handler.handled_ids == [message_id]

    async with session_factory() as verification_session:
        repository = SQLAlchemyOutboxMessageRepository(
            verification_session,
        )

        message = await repository.get_by_id(
            message_id=message_id,
        )

        assert message is not None
        assert message.status == OutboxMessageStatus.PROCESSED.value
        assert message.processed_at == now
        assert message.claim_token is None
        assert message.lease_expires_at is None
        assert message.last_error is None
        assert message.attempt_count == 1


async def test_processing_service_schedules_retry_after_failure(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as cleanup_session:
        await clear_outbox(cleanup_session)

    message_id = await create_pending_message(session_factory)

    handler = FailingHandler(
        error="Temporary provider failure",
    )
    resolver = HandlerResolver(handler)

    policy = OutboxRetryPolicy(
        max_attempts=5,
        base_delay=timedelta(seconds=30),
        max_delay=timedelta(minutes=15),
    )

    service = OutboxProcessingService(
        unit_of_work_factory=lambda: SQLAlchemyOutboxUnitOfWork(session_factory),
        handler_resolver=resolver,
        retry_policy=policy,
        lease_duration=timedelta(minutes=5),
        batch_size=10,
    )

    now = datetime.now(UTC)

    processed_count = await service.process_batch(
        now=now,
    )

    assert processed_count == 1
    assert handler.calls == 1

    async with session_factory() as verification_session:
        repository = SQLAlchemyOutboxMessageRepository(
            verification_session,
        )

        message = await repository.get_by_id(
            message_id=message_id,
        )

        assert message is not None
        assert message.status == OutboxMessageStatus.PENDING.value
        assert message.attempt_count == 1
        assert message.available_at == now + timedelta(seconds=30)
        assert message.claim_token is None
        assert message.lease_expires_at is None
        assert message.processed_at is None
        assert message.last_error == "Temporary provider failure"


async def test_processing_service_uses_exponential_retry_delay(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as cleanup_session:
        await clear_outbox(cleanup_session)

    message_id = await create_pending_message(
        session_factory,
        attempt_count=1,
    )

    handler = FailingHandler(
        error="Still unavailable",
    )
    resolver = HandlerResolver(handler)

    service = OutboxProcessingService(
        unit_of_work_factory=lambda: SQLAlchemyOutboxUnitOfWork(session_factory),
        handler_resolver=resolver,
        retry_policy=OutboxRetryPolicy(
            max_attempts=5,
            base_delay=timedelta(seconds=30),
            max_delay=timedelta(minutes=15),
        ),
        lease_duration=timedelta(minutes=5),
    )

    now = datetime.now(UTC)

    processed_count = await service.process_batch(
        now=now,
    )

    assert processed_count == 1

    async with session_factory() as verification_session:
        repository = SQLAlchemyOutboxMessageRepository(
            verification_session,
        )

        message = await repository.get_by_id(
            message_id=message_id,
        )

        assert message is not None

        # The claim increments attempt_count from 1 to 2.
        assert message.attempt_count == 2

        # Attempt 2 uses 60 seconds.
        assert message.available_at == now + timedelta(seconds=60)

        assert message.status == OutboxMessageStatus.PENDING.value
        assert message.last_error == "Still unavailable"


async def test_processing_service_marks_final_attempt_failed(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as cleanup_session:
        await clear_outbox(cleanup_session)

    # max_attempts=3, so this message has already consumed two attempts.
    message_id = await create_pending_message(
        session_factory,
        attempt_count=2,
    )

    handler = FailingHandler(
        error="Permanent failure",
    )
    resolver = HandlerResolver(handler)

    service = OutboxProcessingService(
        unit_of_work_factory=lambda: SQLAlchemyOutboxUnitOfWork(session_factory),
        handler_resolver=resolver,
        retry_policy=OutboxRetryPolicy(
            max_attempts=3,
        ),
        lease_duration=timedelta(minutes=5),
    )

    now = datetime.now(UTC)

    processed_count = await service.process_batch(
        now=now,
    )

    assert processed_count == 1
    assert handler.calls == 1

    async with session_factory() as verification_session:
        repository = SQLAlchemyOutboxMessageRepository(
            verification_session,
        )

        message = await repository.get_by_id(
            message_id=message_id,
        )

        assert message is not None
        assert message.status == OutboxMessageStatus.FAILED.value
        assert message.attempt_count == 3
        assert message.claim_token is None
        assert message.lease_expires_at is None
        assert message.processed_at is None
        assert message.last_error == "Permanent failure"


async def test_processing_service_returns_zero_when_nothing_is_ready(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as cleanup_session:
        await clear_outbox(cleanup_session)

    handler = SuccessfulHandler()
    resolver = HandlerResolver(handler)

    service = OutboxProcessingService(
        unit_of_work_factory=lambda: SQLAlchemyOutboxUnitOfWork(session_factory),
        handler_resolver=resolver,
        retry_policy=OutboxRetryPolicy(),
        lease_duration=timedelta(minutes=5),
    )

    processed_count = await service.process_batch(
        now=datetime.now(UTC),
    )

    assert processed_count == 0
    assert handler.handled_ids == []
