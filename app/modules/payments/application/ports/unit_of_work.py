from typing import Protocol

from app.modules.billing.application.ports.invoice_repository import (
    InvoiceRepository,
)
from app.modules.customers.application.ports.customer_repository import (
    CustomerRepository,
)
from app.modules.payments.application.ports.payment_allocation_repository import (
    PaymentAllocationRepository,
)
from app.modules.payments.application.ports.payment_repository import (
    PaymentRepository,
)


class PaymentsUnitOfWork(Protocol):
    payments: PaymentRepository
    payment_allocations: PaymentAllocationRepository
    customers: CustomerRepository
    invoices: InvoiceRepository

    async def __aenter__(self) -> "PaymentsUnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
