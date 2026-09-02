from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)
from app.shared.outbox.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyOutboxMessageRepository,
)

pytestmark = pytest.mark.integration


async def create_claimed_message(
    *,
    db_session: AsyncSession,
    claim_token: UUID,
    now: datetime,
) -> OutboxMessage:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    message = OutboxMessage(
        tenant_id=uuid4(),
        event_type=f"processing.lifecycle.{uuid4()}",
        payload={"type": "processing-lifecycle"},
        status=OutboxMessageStatus.PENDING.value,
        attempt_count=0,
        available_at=None,
        claim_token=None,
        lease_expires_at=None,
        processed_at=None,
        last_error=None,
    )

    await repository.add(message)

    claimed = await repository.claim_ready(
        now=now,
        lease_duration=timedelta(minutes=5),
        claim_token=claim_token,
        event_types=(message.event_type,),
        limit=1,
    )

    assert len(claimed) == 1
    assert claimed[0].id == message.id

    return message


async def test_owner_can_mark_message_processed(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    now = datetime.now(UTC)
    claim_token = uuid4()

    message = await create_claimed_message(
        db_session=db_session,
        claim_token=claim_token,
        now=now,
    )

    processed_at = now + timedelta(seconds=1)

    updated = await repository.mark_processed(
        message_id=message.id,
        claim_token=claim_token,
        processed_at=processed_at,
    )

    assert updated is True

    await db_session.refresh(message)

    assert message.status == OutboxMessageStatus.PROCESSED.value
    assert message.processed_at == processed_at
    assert message.claim_token is None
    assert message.lease_expires_at is None
    assert message.last_error is None


async def test_owner_can_release_message_for_retry(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    now = datetime.now(UTC)
    claim_token = uuid4()

    message = await create_claimed_message(
        db_session=db_session,
        claim_token=claim_token,
        now=now,
    )

    retry_at = now + timedelta(minutes=2)

    updated = await repository.release_for_retry(
        message_id=message.id,
        claim_token=claim_token,
        available_at=retry_at,
        error="Temporary provider failure",
    )

    assert updated is True

    await db_session.refresh(message)

    assert message.status == OutboxMessageStatus.PENDING.value
    assert message.available_at == retry_at
    assert message.processed_at is None
    assert message.claim_token is None
    assert message.lease_expires_at is None
    assert message.last_error == "Temporary provider failure"


async def test_owner_can_mark_message_failed(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    now = datetime.now(UTC)
    claim_token = uuid4()

    message = await create_claimed_message(
        db_session=db_session,
        claim_token=claim_token,
        now=now,
    )

    updated = await repository.mark_failed(
        message_id=message.id,
        claim_token=claim_token,
        error="Permanent processing failure",
    )

    assert updated is True

    await db_session.refresh(message)

    assert message.status == OutboxMessageStatus.FAILED.value
    assert message.processed_at is None
    assert message.claim_token is None
    assert message.lease_expires_at is None
    assert message.last_error == "Permanent processing failure"


async def test_stale_worker_cannot_mark_message_processed(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    base_time = datetime.now(UTC)

    old_claim_token = uuid4()
    new_claim_token = uuid4()

    message = await create_claimed_message(
        db_session=db_session,
        claim_token=old_claim_token,
        now=base_time,
    )

    reclaimed = await repository.claim_ready(
        now=base_time + timedelta(minutes=6),
        lease_duration=timedelta(minutes=5),
        claim_token=new_claim_token,
        event_types=(message.event_type,),
        limit=1,
    )

    assert len(reclaimed) == 1
    assert reclaimed[0].id == message.id
    assert message.claim_token == new_claim_token

    updated = await repository.mark_processed(
        message_id=message.id,
        claim_token=old_claim_token,
        processed_at=base_time + timedelta(minutes=7),
    )

    assert updated is False

    await db_session.refresh(message)

    assert message.status == OutboxMessageStatus.PROCESSING.value
    assert message.claim_token == new_claim_token


async def test_stale_worker_cannot_release_message_for_retry(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    base_time = datetime.now(UTC)

    old_claim_token = uuid4()
    new_claim_token = uuid4()

    message = await create_claimed_message(
        db_session=db_session,
        claim_token=old_claim_token,
        now=base_time,
    )

    reclaimed = await repository.claim_ready(
        now=base_time + timedelta(minutes=6),
        lease_duration=timedelta(minutes=5),
        claim_token=new_claim_token,
        event_types=(message.event_type,),
        limit=1,
    )

    assert len(reclaimed) == 1

    updated = await repository.release_for_retry(
        message_id=message.id,
        claim_token=old_claim_token,
        available_at=base_time + timedelta(minutes=10),
        error="Stale worker retry",
    )

    assert updated is False

    await db_session.refresh(message)

    assert message.status == OutboxMessageStatus.PROCESSING.value
    assert message.claim_token == new_claim_token


async def test_stale_worker_cannot_mark_message_failed(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    base_time = datetime.now(UTC)

    old_claim_token = uuid4()
    new_claim_token = uuid4()

    message = await create_claimed_message(
        db_session=db_session,
        claim_token=old_claim_token,
        now=base_time,
    )

    reclaimed = await repository.claim_ready(
        now=base_time + timedelta(minutes=6),
        lease_duration=timedelta(minutes=5),
        claim_token=new_claim_token,
        event_types=(message.event_type,),
        limit=1,
    )

    assert len(reclaimed) == 1

    updated = await repository.mark_failed(
        message_id=message.id,
        claim_token=old_claim_token,
        error="Stale worker failure",
    )

    assert updated is False

    await db_session.refresh(message)

    assert message.status == OutboxMessageStatus.PROCESSING.value
    assert message.claim_token == new_claim_token


async def test_release_for_retry_rejects_blank_error(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    with pytest.raises(
        ValueError,
        match="Retry error cannot be empty",
    ):
        await repository.release_for_retry(
            message_id=uuid4(),
            claim_token=uuid4(),
            available_at=datetime.now(UTC),
            error="   ",
        )


async def test_mark_failed_rejects_blank_error(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    with pytest.raises(
        ValueError,
        match="Failure error cannot be empty",
    ):
        await repository.mark_failed(
            message_id=uuid4(),
            claim_token=uuid4(),
            error="   ",
        )
