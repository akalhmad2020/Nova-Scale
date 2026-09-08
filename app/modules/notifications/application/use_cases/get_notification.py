from dataclasses import dataclass
from uuid import UUID

from app.modules.notifications.application.exceptions import NotificationNotFoundError
from app.modules.notifications.application.ports.repositories import (
    NotificationAttemptRepository,
    NotificationRepository,
)
from app.modules.notifications.infrastructure.models.notification import Notification
from app.modules.notifications.infrastructure.models.notification_attempt import NotificationAttempt


@dataclass(frozen=True, slots=True)
class NotificationDetails:
    notification: Notification
    attempts: tuple[NotificationAttempt, ...]


class GetNotification:
    def __init__(
        self,
        *,
        notifications: NotificationRepository,
        attempts: NotificationAttemptRepository,
    ) -> None:
        self._notifications = notifications
        self._attempts = attempts

    async def execute(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
    ) -> NotificationDetails:
        notification = await self._notifications.get_by_id(
            tenant_id=tenant_id,
            notification_id=notification_id,
        )

        if notification is None:
            raise NotificationNotFoundError

        attempts = await self._attempts.list_for_notification(
            tenant_id=tenant_id,
            notification_id=notification_id,
        )

        return NotificationDetails(
            notification=notification,
            attempts=tuple(attempts),
        )
