from unittest.mock import Mock

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.modules.notifications.infrastructure.outbox.invoice_issued_handler import (
    InvoiceIssuedOutboxHandler,
)
from app.modules.notifications.infrastructure.outbox.registry import (
    INVOICE_ISSUED_EVENT_TYPE,
    build_notification_outbox_handler_registry,
)
from app.shared.outbox.infrastructure.handlers.registry import (
    OutboxMessageHandlerNotConfiguredError,
)


def test_registry_resolves_invoice_issued_handler() -> None:
    session_factory = Mock(
        spec=async_sessionmaker[AsyncSession],
    )

    registry = build_notification_outbox_handler_registry(
        session_factory,
    )

    handler = registry.resolve(
        INVOICE_ISSUED_EVENT_TYPE,
    )

    assert isinstance(
        handler,
        InvoiceIssuedOutboxHandler,
    )


def test_registry_rejects_unknown_event_type() -> None:
    session_factory = Mock(
        spec=async_sessionmaker[AsyncSession],
    )

    registry = build_notification_outbox_handler_registry(
        session_factory,
    )

    with pytest.raises(
        OutboxMessageHandlerNotConfiguredError,
        match="No outbox handler configured",
    ):
        registry.resolve(
            "unknown.event",
        )
