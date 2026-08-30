from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.modules.notifications.infrastructure.outbox.adapters import (
    CreateNotificationFromIntentAdapter,
    SQLAlchemyInvoiceIssuedCustomerResolverAdapter,
)
from app.modules.notifications.infrastructure.outbox.invoice_issued_handler import (
    InvoiceIssuedOutboxHandler,
)
from app.shared.outbox.infrastructure.handlers.registry import (
    OutboxMessageHandlerRegistry,
)

INVOICE_ISSUED_EVENT_TYPE = "invoice.issued"


def build_notification_outbox_handler_registry(
    session_factory: async_sessionmaker[AsyncSession],
) -> OutboxMessageHandlerRegistry:
    customer_resolver = SQLAlchemyInvoiceIssuedCustomerResolverAdapter(
        session_factory,
    )

    create_notification = CreateNotificationFromIntentAdapter(
        session_factory,
    )

    invoice_issued_handler = InvoiceIssuedOutboxHandler(
        customer_resolver=customer_resolver,
        create_notification=create_notification,
    )

    return OutboxMessageHandlerRegistry(
        {
            INVOICE_ISSUED_EVENT_TYPE: invoice_issued_handler,
        }
    )
