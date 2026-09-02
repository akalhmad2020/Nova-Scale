from typing import Protocol

from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)


class OutboxMessageHandler(Protocol):
    async def handle(
        self,
        message: OutboxMessage,
    ) -> None: ...


class OutboxMessageHandlerResolver(Protocol):
    @property
    def event_types(self) -> tuple[str, ...]: ...

    def resolve(
        self,
        event_type: str,
    ) -> OutboxMessageHandler: ...
