from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.notifications.infrastructure.models.notification import (
    Notification,
)
from app.modules.notifications.infrastructure.models.notification_attempt import (
    NotificationAttempt,
)


class NotificationRepository(Protocol):
    async def add(
        self,
        notification: Notification,
    ) -> None: ...

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> Notification | None: ...

    async def get_by_id_for_update(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> Notification | None: ...

    async def get_by_idempotency_key(
        self,
        *,
        tenant_id: UUID,
        idempotency_key: str,
    ) -> Notification | None: ...

    async def list_ready_for_delivery(
        self,
        *,
        tenant_id: UUID,
        now: datetime,
        limit: int = 100,
    ) -> Sequence[Notification]: ...

    async def list_ready_for_delivery_global(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> Sequence[Notification]: ...


class NotificationAttemptRepository(Protocol):
    async def add(
        self,
        attempt: NotificationAttempt,
    ) -> None: ...

    async def list_for_notification(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> Sequence[NotificationAttempt]: ...

    async def get_latest_attempt(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> NotificationAttempt | None: ...
