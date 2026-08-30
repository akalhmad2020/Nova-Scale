from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.shared.outbox.application.ports.handlers import (
    OutboxMessageHandlerResolver,
)
from app.shared.outbox.application.ports.unit_of_work import (
    OutboxUnitOfWork,
)
from app.shared.outbox.application.retry_policy import OutboxRetryPolicy

OutboxUnitOfWorkFactory = Callable[[], OutboxUnitOfWork]


class OutboxProcessingService:
    def __init__(
        self,
        *,
        unit_of_work_factory: OutboxUnitOfWorkFactory,
        handler_resolver: OutboxMessageHandlerResolver,
        retry_policy: OutboxRetryPolicy,
        lease_duration: timedelta,
        batch_size: int = 100,
    ) -> None:
        if lease_duration <= timedelta(0):
            raise ValueError("Lease duration must be positive.")

        if batch_size < 1:
            raise ValueError("Batch size must be at least 1.")

        self._unit_of_work_factory = unit_of_work_factory
        self._handler_resolver = handler_resolver
        self._retry_policy = retry_policy
        self._lease_duration = lease_duration
        self._batch_size = batch_size

    async def process_batch(
        self,
        *,
        now: datetime,
    ) -> int:
        claim_token = uuid4()

        async with self._unit_of_work_factory() as unit_of_work:
            claimed = await unit_of_work.messages.claim_ready(
                now=now,
                lease_duration=self._lease_duration,
                claim_token=claim_token,
                limit=self._batch_size,
            )

            claimed_messages = list(claimed)

            await unit_of_work.commit()

        for message in claimed_messages:
            await self._process_message(
                message_id=message.id,
                event_type=message.event_type,
                attempt_count=message.attempt_count,
                claim_token=claim_token,
                now=now,
            )

        return len(claimed_messages)

    async def _process_message(
        self,
        *,
        message_id: UUID,
        event_type: str,
        attempt_count: int,
        claim_token: UUID,
        now: datetime,
    ) -> None:
        handler = self._handler_resolver.resolve(event_type)

        async with self._unit_of_work_factory() as unit_of_work:
            message = await unit_of_work.messages.get_by_id(
                message_id=message_id,
            )

            if message is None:
                await unit_of_work.rollback()
                return

            if message.claim_token != claim_token:
                await unit_of_work.rollback()
                return

            try:
                await handler.handle(message)
            except Exception as exc:
                await unit_of_work.rollback()

                await self._handle_failure(
                    message_id=message_id,
                    claim_token=claim_token,
                    attempt_count=attempt_count,
                    now=now,
                    error=str(exc),
                )
                return

        async with self._unit_of_work_factory() as unit_of_work:
            updated = await unit_of_work.messages.mark_processed(
                message_id=message_id,
                claim_token=claim_token,
                processed_at=now,
            )

            if updated:
                await unit_of_work.commit()
            else:
                await unit_of_work.rollback()

    async def _handle_failure(
        self,
        *,
        message_id: UUID,
        claim_token: UUID,
        attempt_count: int,
        now: datetime,
        error: str,
    ) -> None:
        normalized_error = error.strip() or "Unknown outbox processing error."

        async with self._unit_of_work_factory() as unit_of_work:
            if self._retry_policy.should_retry(
                attempt_count=attempt_count,
            ):
                delay = self._retry_policy.get_delay(
                    attempt_count=attempt_count,
                )

                updated = await unit_of_work.messages.release_for_retry(
                    message_id=message_id,
                    claim_token=claim_token,
                    available_at=now + delay,
                    error=normalized_error,
                )
            else:
                updated = await unit_of_work.messages.mark_failed(
                    message_id=message_id,
                    claim_token=claim_token,
                    error=normalized_error,
                )

            if updated:
                await unit_of_work.commit()
            else:
                await unit_of_work.rollback()
