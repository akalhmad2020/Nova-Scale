from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.application.exceptions import (
    NotificationIdempotencyConflictError,
)
from app.modules.notifications.domain.enums import NotificationStatus
from app.modules.notifications.infrastructure.models.notification import (
    Notification,
)
from app.modules.notifications.infrastructure.models.notification_attempt import (
    NotificationAttempt,
)

NOTIFICATION_IDEMPOTENCY_CONSTRAINT = "notification_tenant_idempotency_key"


def _get_constraint_name(
    exc: IntegrityError,
) -> str | None:
    original = exc.orig
    diagnostic = getattr(original, "diag", None)

    if diagnostic is not None:
        constraint_name = getattr(
            diagnostic,
            "constraint_name",
            None,
        )

        if isinstance(constraint_name, str):
            return constraint_name

    cause = exc.__cause__

    while cause is not None:
        constraint_name = getattr(
            cause,
            "constraint_name",
            None,
        )

        if isinstance(constraint_name, str):
            return constraint_name

        cause = cause.__cause__

    return None


class SQLAlchemyNotificationRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def add(
        self,
        notification: Notification,
    ) -> None:
        self._session.add(notification)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            constraint_name = _get_constraint_name(exc)

            if constraint_name == NOTIFICATION_IDEMPOTENCY_CONSTRAINT:
                raise NotificationIdempotencyConflictError from exc

            raise

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> Notification | None:
        statement = select(Notification).where(
            Notification.tenant_id == tenant_id,
            Notification.id == notification_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> Notification | None:
        statement = (
            select(Notification)
            .where(
                Notification.tenant_id == tenant_id,
                Notification.id == notification_id,
            )
            .with_for_update()
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_idempotency_key(
        self,
        *,
        tenant_id: UUID,
        idempotency_key: str,
    ) -> Notification | None:
        statement = select(Notification).where(
            Notification.tenant_id == tenant_id,
            Notification.idempotency_key == idempotency_key,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def list_ready_for_delivery(
        self,
        *,
        tenant_id: UUID,
        now: datetime,
        limit: int = 100,
    ) -> Sequence[Notification]:
        statement = (
            select(Notification)
            .where(
                Notification.tenant_id == tenant_id,
                Notification.status == NotificationStatus.PENDING.value,
                (Notification.scheduled_at.is_(None) | (Notification.scheduled_at <= now)),
            )
            .order_by(
                Notification.scheduled_at.asc().nullsfirst(),
                Notification.created_at.asc(),
            )
            .limit(limit)
        )

        result = await self._session.execute(statement)

        return result.scalars().all()

    async def list_ready_for_delivery_global(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> Sequence[Notification]:
        statement = (
            select(Notification)
            .where(
                Notification.status == NotificationStatus.PENDING.value,
                (Notification.scheduled_at.is_(None) | (Notification.scheduled_at <= now)),
            )
            .order_by(
                Notification.scheduled_at.asc().nullsfirst(),
                Notification.created_at.asc(),
            )
            .limit(limit)
        )

        result = await self._session.execute(statement)

        return result.scalars().all()


class SQLAlchemyNotificationAttemptRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def add(
        self,
        attempt: NotificationAttempt,
    ) -> None:
        self._session.add(attempt)
        await self._session.flush()

    async def list_for_notification(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> Sequence[NotificationAttempt]:
        statement = (
            select(NotificationAttempt)
            .where(
                NotificationAttempt.tenant_id == tenant_id,
                NotificationAttempt.notification_id == notification_id,
            )
            .order_by(
                NotificationAttempt.attempt_number.asc(),
            )
        )

        result = await self._session.execute(statement)

        return result.scalars().all()

    async def get_latest_attempt(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> NotificationAttempt | None:
        statement = (
            select(NotificationAttempt)
            .where(
                NotificationAttempt.tenant_id == tenant_id,
                NotificationAttempt.notification_id == notification_id,
            )
            .order_by(
                NotificationAttempt.attempt_number.desc(),
            )
            .limit(1)
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()
