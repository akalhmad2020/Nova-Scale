from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.audit.application.ports.repositories import AuditLogRepository
from app.modules.audit.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyAuditLogRepository,
)
from app.modules.billing.application.ports.invoice_repository import (
    InvoiceRepository,
)
from app.modules.billing.infrastructure.repositories.invoice_repository import (
    SQLAlchemyInvoiceRepository,
)
from app.modules.customers.application.ports.customer_repository import (
    CustomerRepository as CustomerRepositoryPort,
)
from app.modules.customers.infrastructure.repositories.customer_repository import (
    CustomerRepository as SQLAlchemyCustomerRepository,
)
from app.modules.ledger.application.ports.repositories import (
    JournalEntryRepository,
    JournalLineRepository,
    LedgerAccountRepository,
)
from app.modules.ledger.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyJournalEntryRepository,
    SQLAlchemyJournalLineRepository,
    SQLAlchemyLedgerAccountRepository,
)
from app.modules.payments.application.ports.payment_allocation_repository import (
    PaymentAllocationRepository,
)
from app.modules.payments.application.ports.payment_repository import (
    PaymentRepository,
)
from app.modules.payments.infrastructure.repositories.payment_allocation_repository import (
    SQLAlchemyPaymentAllocationRepository,
)
from app.modules.payments.infrastructure.repositories.payment_repository import (
    SQLAlchemyPaymentRepository,
)


class SQLAlchemyPaymentsUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session = session_factory()

        self.payments: PaymentRepository = SQLAlchemyPaymentRepository(self._session)
        self.payment_allocations: PaymentAllocationRepository = (
            SQLAlchemyPaymentAllocationRepository(self._session)
        )
        self.customers: CustomerRepositoryPort = SQLAlchemyCustomerRepository(self._session)
        self.invoices: InvoiceRepository = SQLAlchemyInvoiceRepository(self._session)

        self.ledger_accounts: LedgerAccountRepository = SQLAlchemyLedgerAccountRepository(
            self._session
        )
        self.journal_entries: JournalEntryRepository = SQLAlchemyJournalEntryRepository(
            self._session
        )
        self.journal_lines: JournalLineRepository = SQLAlchemyJournalLineRepository(self._session)

        self.audit_logs: AuditLogRepository = SQLAlchemyAuditLogRepository(self._session)

    async def __aenter__(self) -> "SQLAlchemyPaymentsUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
