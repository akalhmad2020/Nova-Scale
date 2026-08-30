from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)
from app.shared.outbox.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyOutboxMessageRepository,
)

pytestmark = pytest.mark.integration


def make_message(
    *,
    event_type: str,
    status: OutboxMessageStatus = OutboxMessageStatus.PENDING,
    attempt_count: int = 0,
    available_at: datetime | None = None,
    claim_token: UUID | None = None,
    lease_expires_at: datetime | None = None,
) -> OutboxMessage:
    return OutboxMessage(
        tenant_id=uuid4(),
        event_type=event_type,
        payload={
            "event_type": event_type,
        },
        status=status.value,
        attempt_count=attempt_count,
        available_at=available_at,
        claim_token=claim_token,
        lease_expires_at=lease_expires_at,
        processed_at=None,
        last_error=None,
    )


async def clear_outbox(
    session: AsyncSession,
) -> None:
    await session.execute(
        delete(OutboxMessage),
    )
    await session.commit()


async def test_claim_ready_marks_message_processing(
    db_session: AsyncSession,
) -> None:
    await clear_outbox(db_session)

    repository = SQLAlchemyOutboxMessageRepository(db_session)

    now = datetime.now(UTC)
    lease_duration = timedelta(minutes=5)
    claim_token = uuid4()

    message = make_message(
        event_type=f"claim.processing.{uuid4()}",
    )

    await repository.add(message)

    claimed = await repository.claim_ready(
        now=now,
        lease_duration=lease_duration,
        claim_token=claim_token,
        limit=1,
    )

    assert len(claimed) == 1

    claimed_message = claimed[0]

    assert claimed_message.id == message.id
    assert claimed_message.status == OutboxMessageStatus.PROCESSING.value
    assert claimed_message.attempt_count == 1
    assert claimed_message.claim_token == claim_token
    assert claimed_message.lease_expires_at == now + lease_duration
    assert claimed_message.processed_at is None


async def test_claim_ready_ignores_future_pending_message(
    db_session: AsyncSession,
) -> None:
    await clear_outbox(db_session)

    repository = SQLAlchemyOutboxMessageRepository(db_session)

    now = datetime.now(UTC)
    claim_token = uuid4()

    future = make_message(
        event_type=f"claim.future.{uuid4()}",
        available_at=now + timedelta(hours=1),
    )

    await repository.add(future)

    claimed = await repository.claim_ready(
        now=now,
        lease_duration=timedelta(minutes=5),
        claim_token=claim_token,
    )

    assert claimed == []
    assert future.status == OutboxMessageStatus.PENDING.value
    assert future.attempt_count == 0
    assert future.claim_token is None
    assert future.lease_expires_at is None


async def test_claim_ready_does_not_reclaim_active_lease(
    db_session: AsyncSession,
) -> None:
    await clear_outbox(db_session)

    repository = SQLAlchemyOutboxMessageRepository(db_session)

    now = datetime.now(UTC)

    active_claim_token = uuid4()
    new_claim_token = uuid4()

    processing = make_message(
        event_type=f"claim.active.{uuid4()}",
        status=OutboxMessageStatus.PROCESSING,
        attempt_count=1,
        claim_token=active_claim_token,
        lease_expires_at=now + timedelta(minutes=5),
    )

    await repository.add(processing)

    claimed = await repository.claim_ready(
        now=now,
        lease_duration=timedelta(minutes=5),
        claim_token=new_claim_token,
    )

    assert claimed == []
    assert processing.status == OutboxMessageStatus.PROCESSING.value
    assert processing.attempt_count == 1
    assert processing.claim_token == active_claim_token
    assert processing.lease_expires_at == now + timedelta(minutes=5)


async def test_claim_ready_reclaims_expired_lease(
    db_session: AsyncSession,
) -> None:
    await clear_outbox(db_session)

    repository = SQLAlchemyOutboxMessageRepository(db_session)

    now = datetime.now(UTC)
    lease_duration = timedelta(minutes=10)

    old_claim_token = uuid4()
    new_claim_token = uuid4()

    processing = make_message(
        event_type=f"claim.expired.{uuid4()}",
        status=OutboxMessageStatus.PROCESSING,
        attempt_count=1,
        claim_token=old_claim_token,
        lease_expires_at=now - timedelta(seconds=1),
    )

    await repository.add(processing)

    claimed = await repository.claim_ready(
        now=now,
        lease_duration=lease_duration,
        claim_token=new_claim_token,
    )

    assert len(claimed) == 1
    assert claimed[0].id == processing.id

    assert processing.status == OutboxMessageStatus.PROCESSING.value
    assert processing.attempt_count == 2
    assert processing.claim_token == new_claim_token
    assert processing.claim_token != old_claim_token
    assert processing.lease_expires_at == now + lease_duration


async def test_claim_ready_respects_limit(
    db_session: AsyncSession,
) -> None:
    await clear_outbox(db_session)

    repository = SQLAlchemyOutboxMessageRepository(db_session)

    now = datetime.now(UTC)
    lease_duration = timedelta(minutes=5)
    claim_token = uuid4()

    for index in range(3):
        await repository.add(
            make_message(
                event_type=f"claim.limit.{index}.{uuid4()}",
            )
        )

    claimed = await repository.claim_ready(
        now=now,
        lease_duration=lease_duration,
        claim_token=claim_token,
        limit=2,
    )

    assert len(claimed) == 2

    for claimed_message in claimed:
        assert claimed_message.status == OutboxMessageStatus.PROCESSING.value
        assert claimed_message.attempt_count == 1
        assert claimed_message.claim_token == claim_token
        assert claimed_message.lease_expires_at == now + lease_duration


async def test_claim_ready_rejects_non_positive_lease_duration(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    now = datetime.now(UTC)
    claim_token = uuid4()

    with pytest.raises(
        ValueError,
        match="Lease duration must be positive",
    ):
        await repository.claim_ready(
            now=now,
            lease_duration=timedelta(0),
            claim_token=claim_token,
        )

    with pytest.raises(
        ValueError,
        match="Lease duration must be positive",
    ):
        await repository.claim_ready(
            now=now,
            lease_duration=timedelta(seconds=-1),
            claim_token=claim_token,
        )


async def test_claim_ready_rejects_invalid_limit(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    with pytest.raises(
        ValueError,
        match="Claim limit must be at least 1",
    ):
        await repository.claim_ready(
            now=datetime.now(UTC),
            lease_duration=timedelta(minutes=5),
            claim_token=uuid4(),
            limit=0,
        )


async def test_concurrent_workers_claim_different_messages(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime.now(UTC)
    lease_duration = timedelta(minutes=5)

    first_claim_token = uuid4()
    second_claim_token = uuid4()

    async with session_factory() as cleanup_session:
        await clear_outbox(cleanup_session)

    message_ids: list[UUID] = []

    async with session_factory() as setup_session:
        repository = SQLAlchemyOutboxMessageRepository(
            setup_session,
        )

        for index in range(4):
            message = make_message(
                event_type=f"claim.concurrent.{index}.{uuid4()}",
            )

            await repository.add(message)
            message_ids.append(message.id)

        await setup_session.commit()

    async with (
        session_factory() as first_session,
        session_factory() as second_session,
    ):
        first_repository = SQLAlchemyOutboxMessageRepository(
            first_session,
        )
        second_repository = SQLAlchemyOutboxMessageRepository(
            second_session,
        )

        first_claimed = await first_repository.claim_ready(
            now=now,
            lease_duration=lease_duration,
            claim_token=first_claim_token,
            limit=2,
        )

        first_ids = {message.id for message in first_claimed}

        assert len(first_ids) == 2

        for message in first_claimed:
            assert message.claim_token == first_claim_token

        second_claimed = await second_repository.claim_ready(
            now=now,
            lease_duration=lease_duration,
            claim_token=second_claim_token,
            limit=2,
        )

        second_ids = {message.id for message in second_claimed}

        assert len(second_ids) == 2

        for message in second_claimed:
            assert message.claim_token == second_claim_token

        assert first_ids.isdisjoint(second_ids)
        assert first_ids | second_ids == set(message_ids)

        await first_session.commit()
        await second_session.commit()

    async with session_factory() as verification_session:
        repository = SQLAlchemyOutboxMessageRepository(
            verification_session,
        )

        for message_id in message_ids:
            persisted_message = await repository.get_by_id(
                message_id=message_id,
            )

            assert persisted_message is not None
            assert persisted_message.status == OutboxMessageStatus.PROCESSING.value
            assert persisted_message.attempt_count == 1
            assert persisted_message.claim_token in {
                first_claim_token,
                second_claim_token,
            }
            assert persisted_message.lease_expires_at == now + lease_duration


async def test_reclaimed_message_replaces_previous_claim_token(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    base_time = datetime.now(UTC)

    first_claim_token = uuid4()
    second_claim_token = uuid4()

    async with session_factory() as cleanup_session:
        await clear_outbox(cleanup_session)

    async with session_factory() as first_session:
        repository = SQLAlchemyOutboxMessageRepository(
            first_session,
        )

        message = make_message(
            event_type=f"claim.reclaim-token.{uuid4()}",
        )

        await repository.add(message)

        first_claimed = await repository.claim_ready(
            now=base_time,
            lease_duration=timedelta(minutes=5),
            claim_token=first_claim_token,
            limit=1,
        )

        assert len(first_claimed) == 1
        assert first_claimed[0].claim_token == first_claim_token

        message_id = message.id

        await first_session.commit()

    reclaim_time = base_time + timedelta(minutes=6)

    async with session_factory() as second_session:
        repository = SQLAlchemyOutboxMessageRepository(
            second_session,
        )

        second_claimed = await repository.claim_ready(
            now=reclaim_time,
            lease_duration=timedelta(minutes=5),
            claim_token=second_claim_token,
            limit=1,
        )

        assert len(second_claimed) == 1

        reclaimed_message = second_claimed[0]

        assert reclaimed_message.id == message_id
        assert reclaimed_message.attempt_count == 2
        assert reclaimed_message.claim_token == second_claim_token
        assert reclaimed_message.claim_token != first_claim_token
        assert reclaimed_message.lease_expires_at == reclaim_time + timedelta(minutes=5)

        await second_session.commit()
