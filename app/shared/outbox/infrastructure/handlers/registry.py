from app.shared.outbox.application.ports.handlers import (
    OutboxMessageHandler,
)


class OutboxMessageHandlerNotConfiguredError(Exception):
    pass


class OutboxMessageHandlerRegistry:
    def __init__(
        self,
        handlers: dict[str, OutboxMessageHandler],
    ) -> None:
        self._handlers = handlers.copy()

    def register(
        self,
        event_type: str,
        handler: OutboxMessageHandler,
    ) -> None:
        self._handlers[event_type] = handler

    def resolve(
        self,
        event_type: str,
    ) -> OutboxMessageHandler:
        handler = self._handlers.get(event_type)

        if handler is None:
            raise OutboxMessageHandlerNotConfiguredError(
                f"No outbox handler configured for event type: {event_type}"
            )

        return handler
