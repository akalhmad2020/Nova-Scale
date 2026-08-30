from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.billing.application.ports.invoice_line_repository import (
    InvoiceLineRepository,
)
from app.modules.billing.application.ports.invoice_repository import (
    InvoiceRepository,
)
from app.modules.billing.infrastructure.repositories.invoice_line_repository import (
    SQLAlchemyInvoiceLineRepository,
)
from app.modules.billing.infrastructure.repositories.invoice_repository import (
    SQLAlchemyInvoiceRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import (
    CustomerRepository,
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
from app.modules.shipments.infrastructure.repositories.shipment_repository import (
    ShipmentRepository,
)
from app.shared.outbox.application.ports.repositories import (
    OutboxMessageRepository,
)
from app.shared.outbox.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyOutboxMessageRepository,
)


class SQLAlchemyBillingUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

        self.invoices: InvoiceRepository
        self.invoice_lines: InvoiceLineRepository
        self.customers: CustomerRepository
        self.shipments: ShipmentRepository

        self.ledger_accounts: LedgerAccountRepository
        self.journal_entries: JournalEntryRepository
        self.journal_lines: JournalLineRepository

        self.outbox_messages: OutboxMessageRepository

    async def __aenter__(self) -> "SQLAlchemyBillingUnitOfWork":
        self._session = self._session_factory()

        self.invoices = SQLAlchemyInvoiceRepository(self._session)
        self.invoice_lines = SQLAlchemyInvoiceLineRepository(self._session)

        self.customers = CustomerRepository(self._session)
        self.shipments = ShipmentRepository(self._session)

        self.ledger_accounts = SQLAlchemyLedgerAccountRepository(
            self._session,
        )
        self.journal_entries = SQLAlchemyJournalEntryRepository(
            self._session,
        )
        self.journal_lines = SQLAlchemyJournalLineRepository(
            self._session,
        )

        self.outbox_messages = SQLAlchemyOutboxMessageRepository(
            self._session,
        )

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return

        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.rollback()
