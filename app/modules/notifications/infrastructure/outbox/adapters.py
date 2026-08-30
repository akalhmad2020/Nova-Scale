from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.modules.notifications.application.contracts import (
    NotificationIntent,
)
from app.modules.notifications.application.use_cases.create_notification import (
    CreateNotificationUseCase,
)
from app.modules.notifications.application.use_cases.create_notification_from_intent import (
    CreateNotificationFromIntentUseCase,
)
from app.modules.notifications.infrastructure.models.notification import (
    Notification,
)
from app.modules.notifications.infrastructure.outbox.customer_resolver import (
    SQLAlchemyInvoiceIssuedCustomerResolver,
)
from app.modules.notifications.infrastructure.outbox.invoice_issued_handler import (
    InvoiceIssuedCustomer,
)
from app.modules.notifications.infrastructure.unit_of_work import (
    SQLAlchemyNotificationUnitOfWork,
)


class SQLAlchemyInvoiceIssuedCustomerResolverAdapter:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get_customer(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
    ) -> InvoiceIssuedCustomer | None:
        async with self._session_factory() as session:
            resolver = SQLAlchemyInvoiceIssuedCustomerResolver(
                session,
            )

            return await resolver.get_customer(
                tenant_id=tenant_id,
                customer_id=customer_id,
            )


class CreateNotificationFromIntentAdapter:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def execute(
        self,
        *,
        tenant_id: UUID,
        intent: NotificationIntent,
    ) -> Notification:
        async with self._session_factory() as session:
            unit_of_work = SQLAlchemyNotificationUnitOfWork(
                session,
            )

            create_notification = CreateNotificationUseCase(
                unit_of_work,
            )

            create_from_intent = CreateNotificationFromIntentUseCase(
                create_notification,
            )

            return await create_from_intent.execute(
                tenant_id=tenant_id,
                intent=intent,
            )
