from collections.abc import Sequence
from datetime import datetime, timedelta
from types import TracebackType
from typing import cast
from uuid import UUID, uuid4

from app.modules.billing.application.ports.invoice_line_repository import (
    InvoiceLineRepository,
)
from app.modules.billing.application.ports.invoice_repository import (
    InvoiceRepository,
)
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.billing.infrastructure.models.invoice_line import InvoiceLine
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.customers.infrastructure.repositories.customer_repository import (
    CustomerRepository,
)
from app.modules.ledger.application.ports.repositories import (
    JournalEntryRepository,
    JournalLineRepository,
    LedgerAccountRepository,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment
from app.modules.shipments.infrastructure.repositories.shipment_repository import (
    ShipmentRepository,
)
from app.shared.outbox.application.ports.repositories import (
    OutboxMessageRepository,
)
from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)
from tests.unit.ledger.fakes import (
    FakeJournalEntryRepository,
    FakeJournalLineRepository,
    FakeLedgerAccountRepository,
)


class FakeInvoiceRepository:
    def __init__(self) -> None:
        self.items: list[Invoice] = []

    async def add(
        self,
        invoice: Invoice,
    ) -> None:
        invoice.id = uuid4()
        self.items.append(invoice)

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Invoice | None:
        for invoice in self.items:
            if invoice.tenant_id == tenant_id and invoice.id == invoice_id:
                return invoice

        return None

    async def get_by_id_for_update(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Invoice | None:
        return await self.get_by_id(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
        )

    async def get_by_number(
        self,
        *,
        tenant_id: UUID,
        invoice_number: str,
    ) -> Invoice | None:
        for invoice in self.items:
            if invoice.tenant_id == tenant_id and invoice.invoice_number == invoice_number:
                return invoice

        return None

    async def list_by_tenant(
        self,
        *,
        tenant_id: UUID,
    ) -> Sequence[Invoice]:
        return [invoice for invoice in self.items if invoice.tenant_id == tenant_id]

    async def refresh(
        self,
        invoice: Invoice,
    ) -> None:
        return None


class FakeInvoiceLineRepository:
    def __init__(self) -> None:
        self.items: list[InvoiceLine] = []

    async def add(
        self,
        invoice_line: InvoiceLine,
    ) -> None:
        invoice_line.id = uuid4()
        self.items.append(invoice_line)

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        invoice_line_id: UUID,
    ) -> InvoiceLine | None:
        for invoice_line in self.items:
            if invoice_line.tenant_id == tenant_id and invoice_line.id == invoice_line_id:
                return invoice_line

        return None

    async def list_by_invoice(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Sequence[InvoiceLine]:
        return [
            invoice_line
            for invoice_line in self.items
            if (invoice_line.tenant_id == tenant_id and invoice_line.invoice_id == invoice_id)
        ]

    async def delete(
        self,
        invoice_line: InvoiceLine,
    ) -> None:
        self.items.remove(invoice_line)


class FakeCustomerRepository:
    def __init__(self) -> None:
        self.items: list[Customer] = []

    def add_existing(
        self,
        *,
        customer_id: UUID,
        tenant_id: UUID,
    ) -> Customer:
        customer = Customer()
        customer.id = customer_id
        customer.tenant_id = tenant_id

        self.items.append(customer)

        return customer

    async def get_by_id_and_tenant(
        self,
        customer_id: UUID,
        tenant_id: UUID,
    ) -> Customer | None:
        for customer in self.items:
            if customer.id == customer_id and customer.tenant_id == tenant_id:
                return customer

        return None


class FakeShipmentRepository:
    def __init__(self) -> None:
        self.items: list[Shipment] = []

    def add_existing(
        self,
        *,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> Shipment:
        shipment = Shipment()
        shipment.id = shipment_id
        shipment.tenant_id = tenant_id

        self.items.append(shipment)

        return shipment

    async def get_by_id_and_tenant(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> Shipment | None:
        for shipment in self.items:
            if shipment.id == shipment_id and shipment.tenant_id == tenant_id:
                return shipment

        return None


class FakeOutboxMessageRepository:
    def __init__(self) -> None:
        self.items: list[OutboxMessage] = []

    async def add(
        self,
        message: OutboxMessage,
    ) -> None:
        message.id = uuid4()
        self.items.append(message)

    async def get_by_id(
        self,
        *,
        message_id: UUID,
    ) -> OutboxMessage | None:
        for message in self.items:
            if message.id == message_id:
                return message

        return None

    async def get_by_id_for_update(
        self,
        *,
        message_id: UUID,
    ) -> OutboxMessage | None:
        return await self.get_by_id(
            message_id=message_id,
        )

    async def list_ready(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> Sequence[OutboxMessage]:
        ready = [
            message
            for message in self.items
            if (
                message.status == OutboxMessageStatus.PENDING.value
                and (message.available_at is None or message.available_at <= now)
            )
        ]

        return ready[:limit]

    async def claim_ready(
        self,
        *,
        now: datetime,
        lease_duration: timedelta,
        claim_token: UUID,
        limit: int = 100,
    ) -> Sequence[OutboxMessage]:
        claimed: list[OutboxMessage] = []

        for message in self.items:
            if len(claimed) >= limit:
                break

            pending_and_ready = message.status == OutboxMessageStatus.PENDING.value and (
                message.available_at is None or message.available_at <= now
            )

            expired_processing = (
                message.status == OutboxMessageStatus.PROCESSING.value
                and message.lease_expires_at is not None
                and message.lease_expires_at <= now
            )

            if not (pending_and_ready or expired_processing):
                continue

            message.status = OutboxMessageStatus.PROCESSING.value
            message.attempt_count += 1
            message.claim_token = claim_token
            message.lease_expires_at = now + lease_duration

            claimed.append(message)

        return claimed

    async def mark_processed(
        self,
        *,
        message_id: UUID,
        claim_token: UUID,
        processed_at: datetime,
    ) -> bool:
        message = await self.get_by_id(
            message_id=message_id,
        )

        if (
            message is None
            or message.status != OutboxMessageStatus.PROCESSING.value
            or message.claim_token != claim_token
        ):
            return False

        message.status = OutboxMessageStatus.PROCESSED.value
        message.processed_at = processed_at
        message.claim_token = None
        message.lease_expires_at = None
        message.last_error = None

        return True

    async def release_for_retry(
        self,
        *,
        message_id: UUID,
        claim_token: UUID,
        available_at: datetime,
        error: str,
    ) -> bool:
        message = await self.get_by_id(
            message_id=message_id,
        )

        if (
            message is None
            or message.status != OutboxMessageStatus.PROCESSING.value
            or message.claim_token != claim_token
        ):
            return False

        message.status = OutboxMessageStatus.PENDING.value
        message.available_at = available_at
        message.claim_token = None
        message.lease_expires_at = None
        message.last_error = error

        return True

    async def mark_failed(
        self,
        *,
        message_id: UUID,
        claim_token: UUID,
        error: str,
    ) -> bool:
        message = await self.get_by_id(
            message_id=message_id,
        )

        if (
            message is None
            or message.status != OutboxMessageStatus.PROCESSING.value
            or message.claim_token != claim_token
        ):
            return False

        message.status = OutboxMessageStatus.FAILED.value
        message.claim_token = None
        message.lease_expires_at = None
        message.last_error = error

        return True


class FakeBillingUnitOfWork:
    def __init__(self) -> None:
        self.fake_invoices = FakeInvoiceRepository()
        self.fake_invoice_lines = FakeInvoiceLineRepository()
        self.fake_customers = FakeCustomerRepository()
        self.fake_shipments = FakeShipmentRepository()

        self.fake_ledger_accounts = FakeLedgerAccountRepository()
        self.fake_journal_entries = FakeJournalEntryRepository()
        self.fake_journal_lines = FakeJournalLineRepository()

        self.fake_outbox_messages = FakeOutboxMessageRepository()

        self.invoices: InvoiceRepository = self.fake_invoices
        self.invoice_lines: InvoiceLineRepository = self.fake_invoice_lines

        self.customers: CustomerRepository = cast(
            CustomerRepository,
            self.fake_customers,
        )
        self.shipments: ShipmentRepository = cast(
            ShipmentRepository,
            self.fake_shipments,
        )

        self.ledger_accounts: LedgerAccountRepository = self.fake_ledger_accounts
        self.journal_entries: JournalEntryRepository = self.fake_journal_entries
        self.journal_lines: JournalLineRepository = self.fake_journal_lines

        self.outbox_messages: OutboxMessageRepository = self.fake_outbox_messages

        self.committed = False
        self.rolled_back = False

    async def __aenter__(
        self,
    ) -> "FakeBillingUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
