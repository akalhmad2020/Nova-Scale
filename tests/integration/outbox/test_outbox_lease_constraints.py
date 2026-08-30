from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)

pytestmark = pytest.mark.integration


def make_message(
    *,
    status: OutboxMessageStatus,
    claim_token: UUID | None,
    lease_expires_at: datetime | None,
) -> OutboxMessage:
    return OutboxMessage(
        tenant_id=uuid4(),
        event_type=f"lease.test.{uuid4()}",
        payload={"type": "lease-test"},
        status=status.value,
        attempt_count=0,
        available_at=None,
        claim_token=claim_token,
        lease_expires_at=lease_expires_at,
        processed_at=None,
        last_error=None,
    )


async def test_processing_message_requires_claim_token(
    db_session: AsyncSession,
) -> None:
    message = make_message(
        status=OutboxMessageStatus.PROCESSING,
        claim_token=None,
        lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    db_session.add(message)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_processing_message_requires_lease(
    db_session: AsyncSession,
) -> None:
    message = make_message(
        status=OutboxMessageStatus.PROCESSING,
        claim_token=uuid4(),
        lease_expires_at=None,
    )

    db_session.add(message)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_processing_message_requires_claim_token_and_lease(
    db_session: AsyncSession,
) -> None:
    message = make_message(
        status=OutboxMessageStatus.PROCESSING,
        claim_token=None,
        lease_expires_at=None,
    )

    db_session.add(message)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_processing_message_allows_claim_token_and_lease(
    db_session: AsyncSession,
) -> None:
    claim_token = uuid4()
    lease_expires_at = datetime.now(UTC) + timedelta(minutes=5)

    message = make_message(
        status=OutboxMessageStatus.PROCESSING,
        claim_token=claim_token,
        lease_expires_at=lease_expires_at,
    )

    db_session.add(message)
    await db_session.flush()

    assert message.id is not None
    assert message.status == OutboxMessageStatus.PROCESSING.value
    assert message.claim_token == claim_token
    assert message.lease_expires_at == lease_expires_at


@pytest.mark.parametrize(
    "status",
    [
        OutboxMessageStatus.PENDING,
        OutboxMessageStatus.PROCESSED,
        OutboxMessageStatus.FAILED,
    ],
)
async def test_non_processing_message_rejects_claim_token(
    db_session: AsyncSession,
    status: OutboxMessageStatus,
) -> None:
    message = make_message(
        status=status,
        claim_token=uuid4(),
        lease_expires_at=None,
    )

    db_session.add(message)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.parametrize(
    "status",
    [
        OutboxMessageStatus.PENDING,
        OutboxMessageStatus.PROCESSED,
        OutboxMessageStatus.FAILED,
    ],
)
async def test_non_processing_message_rejects_lease(
    db_session: AsyncSession,
    status: OutboxMessageStatus,
) -> None:
    message = make_message(
        status=status,
        claim_token=None,
        lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    db_session.add(message)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.parametrize(
    "status",
    [
        OutboxMessageStatus.PENDING,
        OutboxMessageStatus.PROCESSED,
        OutboxMessageStatus.FAILED,
    ],
)
async def test_non_processing_message_rejects_claim_token_and_lease(
    db_session: AsyncSession,
    status: OutboxMessageStatus,
) -> None:
    message = make_message(
        status=status,
        claim_token=uuid4(),
        lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    db_session.add(message)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.parametrize(
    "status",
    [
        OutboxMessageStatus.PENDING,
        OutboxMessageStatus.PROCESSED,
        OutboxMessageStatus.FAILED,
    ],
)
async def test_non_processing_message_allows_null_claim_state(
    db_session: AsyncSession,
    status: OutboxMessageStatus,
) -> None:
    message = make_message(
        status=status,
        claim_token=None,
        lease_expires_at=None,
    )

    db_session.add(message)
    await db_session.flush()

    assert message.id is not None
    assert message.status == status.value
    assert message.claim_token is None
    assert message.lease_expires_at is None
