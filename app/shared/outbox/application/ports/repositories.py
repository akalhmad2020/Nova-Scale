from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)


class OutboxMessageRepository(Protocol):
    async def add(
        self,
        message: OutboxMessage,
    ) -> None: ...

    async def get_by_id(
        self,
        *,
        message_id: UUID,
    ) -> OutboxMessage | None: ...

    async def get_by_id_for_update(
        self,
        *,
        message_id: UUID,
    ) -> OutboxMessage | None: ...

    async def list_ready(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> Sequence[OutboxMessage]: ...

    async def claim_ready(
        self,
        *,
        now: datetime,
        lease_duration: timedelta,
        claim_token: UUID,
        limit: int = 100,
        event_types: tuple[str, ...],
    ) -> Sequence[OutboxMessage]: ...

    async def mark_processed(
        self,
        *,
        message_id: UUID,
        claim_token: UUID,
        processed_at: datetime,
    ) -> bool: ...

    async def release_for_retry(
        self,
        *,
        message_id: UUID,
        claim_token: UUID,
        available_at: datetime,
        error: str,
    ) -> bool: ...

    async def mark_failed(
        self,
        *,
        message_id: UUID,
        claim_token: UUID,
        error: str,
    ) -> bool: ...
