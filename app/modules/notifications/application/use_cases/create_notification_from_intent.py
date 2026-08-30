from uuid import UUID

from app.modules.notifications.application.contracts import (
    NotificationIntent,
)
from app.modules.notifications.application.use_cases.create_notification import (
    CreateNotificationUseCase,
)
from app.modules.notifications.infrastructure.models.notification import (
    Notification,
)


class CreateNotificationFromIntentUseCase:
    def __init__(
        self,
        create_notification: CreateNotificationUseCase,
    ) -> None:
        self._create_notification = create_notification

    async def execute(
        self,
        *,
        tenant_id: UUID,
        intent: NotificationIntent,
    ) -> Notification:
        return await self._create_notification.execute(
            tenant_id=tenant_id,
            event_type=intent.event_type,
            recipient=intent.recipient,
            channel=intent.channel,
            subject=intent.subject,
            body=intent.body,
            idempotency_key=intent.idempotency_key,
            scheduled_at=intent.scheduled_at,
        )
