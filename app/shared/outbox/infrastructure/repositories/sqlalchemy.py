from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)


class SQLAlchemyOutboxMessageRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def add(
        self,
        message: OutboxMessage,
    ) -> None:
        self._session.add(message)
        await self._session.flush()

    async def get_by_id(
        self,
        *,
        message_id: UUID,
    ) -> OutboxMessage | None:
        statement = select(OutboxMessage).where(
            OutboxMessage.id == message_id,
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self,
        *,
        message_id: UUID,
    ) -> OutboxMessage | None:
        statement = (
            select(OutboxMessage)
            .where(
                OutboxMessage.id == message_id,
            )
            .with_for_update()
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_ready(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> Sequence[OutboxMessage]:
        statement = (
            select(OutboxMessage)
            .where(
                OutboxMessage.status == OutboxMessageStatus.PENDING.value,
                (OutboxMessage.available_at.is_(None) | (OutboxMessage.available_at <= now)),
            )
            .order_by(
                OutboxMessage.available_at.asc().nullsfirst(),
                OutboxMessage.created_at.asc(),
            )
            .limit(limit)
        )

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def claim_ready(
        self,
        *,
        now: datetime,
        lease_duration: timedelta,
        claim_token: UUID,
        limit: int = 100,
    ) -> Sequence[OutboxMessage]:
        if lease_duration <= timedelta(0):
            raise ValueError("Lease duration must be positive.")

        if limit < 1:
            raise ValueError("Claim limit must be at least 1.")

        pending_ready = and_(
            OutboxMessage.status == OutboxMessageStatus.PENDING.value,
            (OutboxMessage.available_at.is_(None) | (OutboxMessage.available_at <= now)),
        )

        expired_processing = and_(
            OutboxMessage.status == OutboxMessageStatus.PROCESSING.value,
            OutboxMessage.lease_expires_at.is_not(None),
            OutboxMessage.lease_expires_at <= now,
        )

        statement = (
            select(OutboxMessage)
            .where(
                or_(
                    pending_ready,
                    expired_processing,
                )
            )
            .order_by(
                OutboxMessage.available_at.asc().nullsfirst(),
                OutboxMessage.created_at.asc(),
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        result = await self._session.execute(statement)
        messages = list(result.scalars().all())

        lease_expires_at = now + lease_duration

        for message in messages:
            message.status = OutboxMessageStatus.PROCESSING.value
            message.attempt_count += 1
            message.claim_token = claim_token
            message.lease_expires_at = lease_expires_at
            message.processed_at = None

        await self._session.flush()

        return messages

    async def mark_processed(
        self,
        *,
        message_id: UUID,
        claim_token: UUID,
        processed_at: datetime,
    ) -> bool:
        statement = (
            update(OutboxMessage)
            .where(
                OutboxMessage.id == message_id,
                OutboxMessage.status == OutboxMessageStatus.PROCESSING.value,
                OutboxMessage.claim_token == claim_token,
            )
            .values(
                status=OutboxMessageStatus.PROCESSED.value,
                processed_at=processed_at,
                claim_token=None,
                lease_expires_at=None,
                last_error=None,
            )
            .returning(OutboxMessage.id)
        )

        result = await self._session.execute(statement)
        updated_id = result.scalar_one_or_none()

        return updated_id is not None

    async def release_for_retry(
        self,
        *,
        message_id: UUID,
        claim_token: UUID,
        available_at: datetime,
        error: str,
    ) -> bool:
        normalized_error = error.strip()

        if not normalized_error:
            raise ValueError("Retry error cannot be empty.")

        statement = (
            update(OutboxMessage)
            .where(
                OutboxMessage.id == message_id,
                OutboxMessage.status == OutboxMessageStatus.PROCESSING.value,
                OutboxMessage.claim_token == claim_token,
            )
            .values(
                status=OutboxMessageStatus.PENDING.value,
                available_at=available_at,
                processed_at=None,
                claim_token=None,
                lease_expires_at=None,
                last_error=normalized_error,
            )
            .returning(OutboxMessage.id)
        )

        result = await self._session.execute(statement)
        updated_id = result.scalar_one_or_none()

        return updated_id is not None

    async def mark_failed(
        self,
        *,
        message_id: UUID,
        claim_token: UUID,
        error: str,
    ) -> bool:
        normalized_error = error.strip()

        if not normalized_error:
            raise ValueError("Failure error cannot be empty.")

        statement = (
            update(OutboxMessage)
            .where(
                OutboxMessage.id == message_id,
                OutboxMessage.status == OutboxMessageStatus.PROCESSING.value,
                OutboxMessage.claim_token == claim_token,
            )
            .values(
                status=OutboxMessageStatus.FAILED.value,
                processed_at=None,
                claim_token=None,
                lease_expires_at=None,
                last_error=normalized_error,
            )
            .returning(OutboxMessage.id)
        )

        result = await self._session.execute(statement)
        updated_id = result.scalar_one_or_none()

        return updated_id is not None
