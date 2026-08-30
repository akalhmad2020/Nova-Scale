from types import TracebackType
from typing import Protocol

from app.shared.outbox.application.ports.repositories import (
    OutboxMessageRepository,
)


class OutboxUnitOfWork(Protocol):
    messages: OutboxMessageRepository

    async def __aenter__(self) -> "OutboxUnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
