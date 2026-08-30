from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)
from app.shared.outbox.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyOutboxMessageRepository,
)

pytestmark = pytest.mark.integration


async def test_outbox_message_allows_valid_json_payload(
    db_session: AsyncSession,
) -> None:
    message = OutboxMessage(
        tenant_id=uuid4(),
        event_type="invoice.issued",
        payload={
            "invoice_id": str(uuid4()),
            "customer_id": str(uuid4()),
        },
        status=OutboxMessageStatus.PENDING.value,
        attempt_count=0,
        available_at=None,
        processed_at=None,
        last_error=None,
    )

    db_session.add(message)
    await db_session.flush()

    assert message.id is not None
    assert message.status == OutboxMessageStatus.PENDING.value
    assert message.attempt_count == 0


async def test_outbox_message_rejects_blank_event_type(
    db_session: AsyncSession,
) -> None:
    message = OutboxMessage(
        tenant_id=uuid4(),
        event_type="   ",
        payload={"value": "test"},
        status=OutboxMessageStatus.PENDING.value,
        attempt_count=0,
        available_at=None,
        processed_at=None,
        last_error=None,
    )

    db_session.add(message)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_outbox_message_rejects_negative_attempt_count(
    db_session: AsyncSession,
) -> None:
    message = OutboxMessage(
        tenant_id=uuid4(),
        event_type="invoice.issued",
        payload={"value": "test"},
        status=OutboxMessageStatus.PENDING.value,
        attempt_count=-1,
        available_at=None,
        processed_at=None,
        last_error=None,
    )

    db_session.add(message)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_outbox_message_rejects_invalid_status(
    db_session: AsyncSession,
) -> None:
    message = OutboxMessage(
        tenant_id=uuid4(),
        event_type="invoice.issued",
        payload={"value": "test"},
        status="unknown",
        attempt_count=0,
        available_at=None,
        processed_at=None,
        last_error=None,
    )

    db_session.add(message)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_list_ready_returns_only_ready_pending_messages(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    now = datetime.now(UTC)
    tenant_id = uuid4()

    ready_without_schedule = OutboxMessage(
        tenant_id=tenant_id,
        event_type="ready.no_schedule",
        payload={"type": "ready"},
        status=OutboxMessageStatus.PENDING.value,
        attempt_count=0,
        available_at=None,
        processed_at=None,
        last_error=None,
    )

    ready_in_past = OutboxMessage(
        tenant_id=tenant_id,
        event_type="ready.in_past",
        payload={"type": "ready"},
        status=OutboxMessageStatus.PENDING.value,
        attempt_count=0,
        available_at=now - timedelta(minutes=5),
        processed_at=None,
        last_error=None,
    )

    ready_exactly_now = OutboxMessage(
        tenant_id=tenant_id,
        event_type="ready.now",
        payload={"type": "ready"},
        status=OutboxMessageStatus.PENDING.value,
        attempt_count=0,
        available_at=now,
        processed_at=None,
        last_error=None,
    )

    future = OutboxMessage(
        tenant_id=tenant_id,
        event_type="future",
        payload={"type": "future"},
        status=OutboxMessageStatus.PENDING.value,
        attempt_count=0,
        available_at=now + timedelta(hours=1),
        processed_at=None,
        last_error=None,
    )

    processed = OutboxMessage(
        tenant_id=tenant_id,
        event_type="processed",
        payload={"type": "processed"},
        status=OutboxMessageStatus.PROCESSED.value,
        attempt_count=1,
        available_at=None,
        processed_at=now,
        last_error=None,
    )

    failed = OutboxMessage(
        tenant_id=tenant_id,
        event_type="failed",
        payload={"type": "failed"},
        status=OutboxMessageStatus.FAILED.value,
        attempt_count=3,
        available_at=None,
        processed_at=None,
        last_error="processing failed",
    )

    messages = [
        ready_without_schedule,
        ready_in_past,
        ready_exactly_now,
        future,
        processed,
        failed,
    ]

    for message in messages:
        await repository.add(message)

    ready_messages = await repository.list_ready(
        now=now,
        limit=100,
    )

    ready_ids = {message.id for message in ready_messages}

    assert ready_without_schedule.id in ready_ids
    assert ready_in_past.id in ready_ids
    assert ready_exactly_now.id in ready_ids

    assert future.id not in ready_ids
    assert processed.id not in ready_ids
    assert failed.id not in ready_ids


async def test_list_ready_respects_limit(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    tenant_id = uuid4()
    now = datetime.now(UTC)

    for index in range(5):
        await repository.add(
            OutboxMessage(
                tenant_id=tenant_id,
                event_type=f"event.{index}",
                payload={"index": index},
                status=OutboxMessageStatus.PENDING.value,
                attempt_count=0,
                available_at=None,
                processed_at=None,
                last_error=None,
            )
        )

    messages = await repository.list_ready(
        now=now,
        limit=2,
    )

    assert len(messages) == 2


async def test_get_by_id_returns_message(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    message = OutboxMessage(
        tenant_id=uuid4(),
        event_type="invoice.issued",
        payload={"invoice_id": str(uuid4())},
        status=OutboxMessageStatus.PENDING.value,
        attempt_count=0,
        available_at=None,
        processed_at=None,
        last_error=None,
    )

    await repository.add(message)

    result = await repository.get_by_id(
        message_id=message.id,
    )

    assert result is not None
    assert result.id == message.id
    assert result.event_type == "invoice.issued"


async def test_get_by_id_returns_none_for_unknown_message(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    result = await repository.get_by_id(
        message_id=uuid4(),
    )

    assert result is None


async def test_payload_is_persisted_as_jsonb(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxMessageRepository(db_session)

    payload = {
        "invoice_id": str(uuid4()),
        "notification": {
            "channel": "email",
            "recipient": "billing@example.com",
            "subject": "Invoice issued",
        },
    }

    message = OutboxMessage(
        tenant_id=uuid4(),
        event_type="invoice.issued",
        payload=payload,
        status=OutboxMessageStatus.PENDING.value,
        attempt_count=0,
        available_at=None,
        processed_at=None,
        last_error=None,
    )

    await repository.add(message)

    statement = select(OutboxMessage).where(
        OutboxMessage.id == message.id,
    )

    result = await db_session.execute(statement)
    persisted = result.scalar_one()

    assert persisted.payload == payload
