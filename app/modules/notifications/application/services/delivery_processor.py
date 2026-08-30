from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.application.exceptions import (
    NotificationAlreadyProcessedError,
    NotificationDeliveryError,
    NotificationNotFoundError,
    NotificationNotReadyError,
)
from app.modules.notifications.application.ports.providers import (
    NotificationProviderResolver,
)
from app.modules.notifications.application.use_cases.deliver_notification import (
    DeliverNotificationUseCase,
)
from app.modules.notifications.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyNotificationRepository,
)
from app.modules.notifications.infrastructure.unit_of_work import (
    SQLAlchemyNotificationUnitOfWork,
)


class AsyncSessionContext(Protocol):
    async def __aenter__(self) -> AsyncSession: ...

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None: ...


type SessionFactory = Callable[[], AsyncSessionContext]


@dataclass(frozen=True, slots=True)
class NotificationDeliveryCandidate:
    tenant_id: UUID
    notification_id: UUID


@dataclass(frozen=True, slots=True)
class NotificationDeliveryBatchResult:
    discovered: int
    delivered: int
    retryable_failures: int
    skipped: int
    unexpected_failures: int


class NotificationDeliveryProcessor:
    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        provider_resolver: NotificationProviderResolver,
        batch_size: int = 50,
        max_attempts: int = 3,
        retry_base_seconds: float = 30.0,
        retry_max_seconds: float = 900.0,
    ) -> None:
        if batch_size < 1:
            raise ValueError("Batch size must be at least 1.")

        if max_attempts < 1:
            raise ValueError("Maximum attempts must be at least 1.")

        if retry_base_seconds <= 0:
            raise ValueError("Retry base seconds must be greater than 0.")

        if retry_max_seconds <= 0:
            raise ValueError("Retry maximum seconds must be greater than 0.")

        self._session_factory = session_factory
        self._provider_resolver = provider_resolver
        self._batch_size = batch_size
        self._max_attempts = max_attempts
        self._retry_base_seconds = retry_base_seconds
        self._retry_max_seconds = retry_max_seconds

    async def process_batch(
        self,
    ) -> NotificationDeliveryBatchResult:
        candidates = await self._discover_candidates()

        delivered = 0
        retryable_failures = 0
        skipped = 0
        unexpected_failures = 0

        for candidate in candidates:
            try:
                await self._deliver_candidate(candidate)
            except NotificationDeliveryError:
                retryable_failures += 1
            except (
                NotificationAlreadyProcessedError,
                NotificationNotFoundError,
                NotificationNotReadyError,
            ):
                skipped += 1
            except Exception:
                unexpected_failures += 1
            else:
                delivered += 1

        return NotificationDeliveryBatchResult(
            discovered=len(candidates),
            delivered=delivered,
            retryable_failures=retryable_failures,
            skipped=skipped,
            unexpected_failures=unexpected_failures,
        )

    async def _discover_candidates(
        self,
    ) -> list[NotificationDeliveryCandidate]:
        async with self._session_factory() as session:
            repository = SQLAlchemyNotificationRepository(session)

            notifications = await repository.list_ready_for_delivery_global(
                now=datetime.now(UTC),
                limit=self._batch_size,
            )

            return [
                NotificationDeliveryCandidate(
                    tenant_id=notification.tenant_id,
                    notification_id=notification.id,
                )
                for notification in notifications
            ]

    async def _deliver_candidate(
        self,
        candidate: NotificationDeliveryCandidate,
    ) -> None:
        async with self._session_factory() as session:
            unit_of_work = SQLAlchemyNotificationUnitOfWork(session)

            use_case = DeliverNotificationUseCase(
                unit_of_work=unit_of_work,
                provider_resolver=self._provider_resolver,
                max_attempts=self._max_attempts,
                retry_base_seconds=self._retry_base_seconds,
                retry_max_seconds=self._retry_max_seconds,
            )

            try:
                await use_case.execute(
                    tenant_id=candidate.tenant_id,
                    notification_id=candidate.notification_id,
                )
            except Exception:
                await unit_of_work.rollback()
                raise
