from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.modules.notifications.application.ports.repositories import NotificationRepository
from app.modules.notifications.infrastructure.models.notification import Notification


@dataclass(frozen=True, slots=True)
class ListNotificationsQuery:
    tenant_id: UUID
    limit: int = 50


class ListNotifications:
    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository

    async def execute(self, query: ListNotificationsQuery) -> Sequence[Notification]:
        if query.limit < 1 or query.limit > 200:
            raise ValueError("Notification list limit must be between 1 and 200.")

        return await self._repository.list_by_tenant(
            tenant_id=query.tenant_id,
            limit=query.limit,
        )
