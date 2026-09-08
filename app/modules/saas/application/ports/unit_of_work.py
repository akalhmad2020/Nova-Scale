from types import TracebackType
from typing import Protocol

from app.modules.saas.application.ports.repository import SubscriptionRepository


class SubscriptionUnitOfWork(Protocol):
    @property
    def subscriptions(self) -> SubscriptionRepository: ...

    async def __aenter__(self) -> "SubscriptionUnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
