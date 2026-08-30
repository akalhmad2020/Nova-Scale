from typing import Protocol

from app.modules.notifications.application.ports.repositories import (
    NotificationAttemptRepository,
    NotificationRepository,
)


class NotificationUnitOfWork(Protocol):
    @property
    def notifications(self) -> NotificationRepository: ...

    @property
    def attempts(self) -> NotificationAttemptRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
