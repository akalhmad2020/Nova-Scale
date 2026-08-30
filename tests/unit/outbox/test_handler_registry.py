import pytest

from app.shared.outbox.infrastructure.handlers.registry import (
    OutboxMessageHandlerNotConfiguredError,
    OutboxMessageHandlerRegistry,
)
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)


class FakeHandler:
    async def handle(
        self,
        message: OutboxMessage,
    ) -> None:
        return None


def test_registry_resolves_registered_handler() -> None:
    handler = FakeHandler()

    registry = OutboxMessageHandlerRegistry(
        {
            "invoice.issued": handler,
        }
    )

    resolved = registry.resolve(
        "invoice.issued",
    )

    assert resolved is handler


def test_registry_rejects_unknown_event_type() -> None:
    registry = OutboxMessageHandlerRegistry({})

    with pytest.raises(
        OutboxMessageHandlerNotConfiguredError,
        match="No outbox handler configured",
    ):
        registry.resolve(
            "unknown.event",
        )
