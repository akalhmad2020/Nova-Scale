from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyNotificationAttemptRepository,
    SQLAlchemyNotificationRepository,
)


class SQLAlchemyNotificationUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.notifications = SQLAlchemyNotificationRepository(session)
        self.attempts = SQLAlchemyNotificationAttemptRepository(session)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
