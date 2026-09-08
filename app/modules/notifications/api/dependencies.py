from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.notifications.application.use_cases.get_notification import GetNotification
from app.modules.notifications.application.use_cases.list_notifications import ListNotifications
from app.modules.notifications.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyNotificationAttemptRepository,
    SQLAlchemyNotificationRepository,
)


def get_list_notifications_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ListNotifications:
    return ListNotifications(
        repository=SQLAlchemyNotificationRepository(session),
    )


def get_notification_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GetNotification:
    return GetNotification(
        notifications=SQLAlchemyNotificationRepository(session),
        attempts=SQLAlchemyNotificationAttemptRepository(session),
    )
