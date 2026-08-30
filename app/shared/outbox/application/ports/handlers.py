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
    def resolve(
        self,
        event_type: str,
    ) -> OutboxMessageHandler: ...
