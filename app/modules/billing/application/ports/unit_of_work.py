from types import TracebackType
from typing import Protocol, Self

from app.modules.billing.application.ports.invoice_line_repository import (
    InvoiceLineRepository,
)
from app.modules.billing.application.ports.invoice_repository import (
    InvoiceRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import (
    CustomerRepository,
)
from app.modules.ledger.application.ports.repositories import (
    JournalEntryRepository,
    JournalLineRepository,
    LedgerAccountRepository,
)
from app.modules.shipments.infrastructure.repositories.shipment_repository import (
    ShipmentRepository,
)
from app.shared.outbox.application.ports.repositories import (
    OutboxMessageRepository,
)


class BillingUnitOfWork(Protocol):
    invoices: InvoiceRepository
    invoice_lines: InvoiceLineRepository
    customers: CustomerRepository
    shipments: ShipmentRepository

    ledger_accounts: LedgerAccountRepository
    journal_entries: JournalEntryRepository
    journal_lines: JournalLineRepository

    outbox_messages: OutboxMessageRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
