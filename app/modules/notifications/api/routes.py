from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.notifications.api.dependencies import (
    get_list_notifications_use_case,
    get_notification_use_case,
)
from app.modules.notifications.api.schemas import (
    NotificationAttemptResponse,
    NotificationDetailsResponse,
    NotificationResponse,
)
from app.modules.notifications.application.exceptions import NotificationNotFoundError
from app.modules.notifications.application.use_cases.get_notification import GetNotification
from app.modules.notifications.application.use_cases.list_notifications import (
    ListNotifications,
    ListNotificationsQuery,
)

router = APIRouter(
    prefix="/tenants/{tenant_id}/notifications",
    tags=["notifications"],
)


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    tenant_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.NOTIFICATION_READ)),
    ],
    use_case: Annotated[
        ListNotifications,
        Depends(get_list_notifications_use_case),
    ],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[NotificationResponse]:
    del membership

    notifications = await use_case.execute(
        ListNotificationsQuery(
            tenant_id=tenant_id,
            limit=limit,
        )
    )

    return [NotificationResponse.model_validate(item) for item in notifications]


@router.get("/{notification_id}", response_model=NotificationDetailsResponse)
async def get_notification(
    tenant_id: UUID,
    notification_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.NOTIFICATION_READ)),
    ],
    use_case: Annotated[
        GetNotification,
        Depends(get_notification_use_case),
    ],
) -> NotificationDetailsResponse:
    del membership

    try:
        details = await use_case.execute(
            tenant_id=tenant_id,
            notification_id=notification_id,
        )
    except NotificationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        ) from exc

    notification = NotificationResponse.model_validate(details.notification)

    return NotificationDetailsResponse(
        **notification.model_dump(),
        attempts=[
            NotificationAttemptResponse.model_validate(attempt) for attempt in details.attempts
        ],
    )
