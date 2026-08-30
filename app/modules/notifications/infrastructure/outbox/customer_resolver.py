from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customers.infrastructure.repositories.customer_repository import (
    CustomerRepository,
)
from app.modules.notifications.infrastructure.outbox.invoice_issued_handler import (
    InvoiceIssuedCustomer,
)


class SQLAlchemyInvoiceIssuedCustomerResolver:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._customers = CustomerRepository(session)

    async def get_customer(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
    ) -> InvoiceIssuedCustomer | None:
        customer = await self._customers.get_by_id_and_tenant(
            customer_id=customer_id,
            tenant_id=tenant_id,
        )

        if customer is None:
            return None

        return InvoiceIssuedCustomer(
            id=customer.id,
            email=customer.email,
        )
