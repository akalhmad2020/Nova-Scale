from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.audit.application.ports.repositories import AuditLogRepository
from app.modules.audit.infrastructure.models.audit_log import AuditLog
from app.modules.billing.application.ports.invoice_repository import (
    InvoiceRepository,
)
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.customers.application.ports.customer_repository import (
    CustomerRepository,
)
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.ledger.application.ports.repositories import (
    JournalEntryRepository,
    JournalLineRepository,
    LedgerAccountRepository,
)
from app.modules.payments.application.ports.payment_allocation_repository import (
    PaymentAllocationRepository,
)
from app.modules.payments.application.ports.payment_repository import (
    PaymentRepository,
)
from app.modules.payments.domain.enums import PaymentStatus
from app.modules.payments.infrastructure.models.payment import Payment
from app.modules.payments.infrastructure.models.payment_allocation import (
    PaymentAllocation,
)
from tests.unit.ledger.fakes import (
    FakeJournalEntryRepository,
    FakeJournalLineRepository,
    FakeLedgerAccountRepository,
)


class FakePaymentRepository:
    def __init__(self) -> None:
        self.items: list[Payment] = []

    async def add(
        self,
        payment: Payment,
    ) -> None:
        self.items.append(payment)

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
    ) -> Payment | None:
        return next(
            (
                payment
                for payment in self.items
                if payment.tenant_id == tenant_id and payment.id == payment_id
            ),
            None,
        )

    async def get_by_id_for_update(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
    ) -> Payment | None:
        return await self.get_by_id(
            tenant_id=tenant_id,
            payment_id=payment_id,
        )

    async def get_by_number(
        self,
        *,
        tenant_id: UUID,
        payment_number: str,
    ) -> Payment | None:
        return next(
            (
                payment
                for payment in self.items
                if payment.tenant_id == tenant_id and payment.payment_number == payment_number
            ),
            None,
        )

    async def list_by_tenant(
        self,
        *,
        tenant_id: UUID,
    ) -> list[Payment]:
        return [payment for payment in self.items if payment.tenant_id == tenant_id]

    async def refresh(
        self,
        payment: Payment,
    ) -> None:
        return None


class FakePaymentAllocationRepository:
    def __init__(
        self,
        payments: FakePaymentRepository,
    ) -> None:
        self.items: list[PaymentAllocation] = []
        self._payments = payments

    async def add(
        self,
        payment_allocation: PaymentAllocation,
    ) -> None:
        self.items.append(payment_allocation)

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        payment_allocation_id: UUID,
    ) -> PaymentAllocation | None:
        return next(
            (
                allocation
                for allocation in self.items
                if allocation.tenant_id == tenant_id and allocation.id == payment_allocation_id
            ),
            None,
        )

    async def get_by_payment_and_invoice(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
        invoice_id: UUID,
    ) -> PaymentAllocation | None:
        return next(
            (
                allocation
                for allocation in self.items
                if allocation.tenant_id == tenant_id
                and allocation.payment_id == payment_id
                and allocation.invoice_id == invoice_id
            ),
            None,
        )

    async def list_by_payment(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
    ) -> list[PaymentAllocation]:
        return [
            allocation
            for allocation in self.items
            if allocation.tenant_id == tenant_id and allocation.payment_id == payment_id
        ]

    async def list_by_invoice(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> list[PaymentAllocation]:
        return [
            allocation
            for allocation in self.items
            if allocation.tenant_id == tenant_id and allocation.invoice_id == invoice_id
        ]

    async def sum_posted_by_invoice(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Decimal:
        total = Decimal("0.00")

        for allocation in self.items:
            if allocation.tenant_id != tenant_id or allocation.invoice_id != invoice_id:
                continue

            payment = await self._payments.get_by_id(
                tenant_id=tenant_id,
                payment_id=allocation.payment_id,
            )

            if payment is not None and payment.status == PaymentStatus.POSTED:
                total += allocation.amount

        return total

    async def delete(
        self,
        payment_allocation: PaymentAllocation,
    ) -> None:
        self.items.remove(payment_allocation)


class FakeCustomerRepository:
    def __init__(self) -> None:
        self.items: list[Customer] = []

    async def get_by_id(
        self,
        customer_id: UUID,
    ) -> Customer | None:
        return next(
            (customer for customer in self.items if customer.id == customer_id),
            None,
        )

    async def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: UUID,
    ) -> Customer | None:
        return next(
            (
                customer
                for customer in self.items
                if customer.code == code and customer.tenant_id == tenant_id
            ),
            None,
        )

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Customer]:
        return [customer for customer in self.items if customer.tenant_id == tenant_id]

    def add(
        self,
        customer: Customer,
    ) -> None:
        self.items.append(customer)

    async def get_by_id_and_tenant(
        self,
        customer_id: UUID,
        tenant_id: UUID,
    ) -> Customer | None:
        return next(
            (
                customer
                for customer in self.items
                if customer.id == customer_id and customer.tenant_id == tenant_id
            ),
            None,
        )


class FakeInvoiceRepository:
    def __init__(self) -> None:
        self.items: list[Invoice] = []

    async def add(
        self,
        invoice: Invoice,
    ) -> None:
        self.items.append(invoice)

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Invoice | None:
        return next(
            (
                invoice
                for invoice in self.items
                if invoice.tenant_id == tenant_id and invoice.id == invoice_id
            ),
            None,
        )

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
        return next(
            (
                invoice
                for invoice in self.items
                if invoice.tenant_id == tenant_id and invoice.invoice_number == invoice_number
            ),
            None,
        )

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


class FakeAuditLogRepository:
    def __init__(self) -> None:
        self.items: list[AuditLog] = []

    async def add(
        self,
        audit_log: AuditLog,
    ) -> None:
        self.items.append(audit_log)

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        audit_log_id: UUID,
    ) -> AuditLog | None:
        return next(
            (
                audit_log
                for audit_log in self.items
                if audit_log.tenant_id == tenant_id and audit_log.id == audit_log_id
            ),
            None,
        )

    async def list_for_tenant(
        self,
        *,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
        actor_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> Sequence[AuditLog]:
        items = [audit_log for audit_log in self.items if audit_log.tenant_id == tenant_id]

        if actor_id is not None:
            items = [audit_log for audit_log in items if audit_log.actor_id == actor_id]

        if action is not None:
            items = [audit_log for audit_log in items if audit_log.action == action]

        if resource_type is not None:
            items = [audit_log for audit_log in items if audit_log.resource_type == resource_type]

        if resource_id is not None:
            items = [audit_log for audit_log in items if audit_log.resource_id == resource_id]

        if occurred_from is not None:
            items = [audit_log for audit_log in items if audit_log.occurred_at >= occurred_from]

        if occurred_to is not None:
            items = [audit_log for audit_log in items if audit_log.occurred_at <= occurred_to]

        items.sort(
            key=lambda audit_log: (
                audit_log.occurred_at,
                audit_log.id,
            ),
            reverse=True,
        )

        return items[offset : offset + limit]


class FakePaymentsUnitOfWork:
    payments: PaymentRepository
    payment_allocations: PaymentAllocationRepository
    customers: CustomerRepository
    invoices: InvoiceRepository

    ledger_accounts: LedgerAccountRepository
    journal_entries: JournalEntryRepository
    journal_lines: JournalLineRepository

    audit_logs: AuditLogRepository

    def __init__(self) -> None:
        self.fake_payments = FakePaymentRepository()

        self.fake_payment_allocations = FakePaymentAllocationRepository(
            self.fake_payments,
        )

        self.fake_customers = FakeCustomerRepository()
        self.fake_invoices = FakeInvoiceRepository()

        self.payments = self.fake_payments
        self.payment_allocations = self.fake_payment_allocations
        self.customers = self.fake_customers
        self.invoices = self.fake_invoices

        self.fake_ledger_accounts = FakeLedgerAccountRepository()
        self.fake_journal_entries = FakeJournalEntryRepository()
        self.fake_journal_lines = FakeJournalLineRepository()

        self.ledger_accounts: LedgerAccountRepository = self.fake_ledger_accounts
        self.journal_entries: JournalEntryRepository = self.fake_journal_entries
        self.journal_lines: JournalLineRepository = self.fake_journal_lines

        self.fake_audit_logs = FakeAuditLogRepository()
        self.audit_logs: AuditLogRepository = self.fake_audit_logs

        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> "FakePaymentsUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
