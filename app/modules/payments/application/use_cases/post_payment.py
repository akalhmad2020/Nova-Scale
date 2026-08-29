from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.ledger.application.exceptions import LedgerAccountNotFoundError
from app.modules.ledger.application.services import (
    JournalLineInput,
    JournalPostingService,
)
from app.modules.ledger.domain.enums import (
    JournalSourceType,
    LedgerAccountPurpose,
)
from app.modules.ledger.infrastructure.models import LedgerAccount
from app.modules.payments.application.ports.unit_of_work import (
    PaymentsUnitOfWork,
)
from app.modules.payments.domain.enums import PaymentStatus
from app.modules.payments.domain.exceptions import (
    InvalidInvoiceForPaymentError,
    InvalidPaymentStateTransitionError,
    PaymentAllocationExceedsInvoiceError,
    PaymentAllocationExceedsPaymentError,
    PaymentCurrencyMismatchError,
    PaymentNotFoundError,
    PaymentNotFullyAllocatedError,
)
from app.modules.payments.infrastructure.models.payment import Payment


class PostPaymentUseCase:
    def __init__(self, unit_of_work: PaymentsUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
    ) -> Payment:
        async with self._unit_of_work:
            payment = await self._unit_of_work.payments.get_by_id_for_update(
                tenant_id=tenant_id,
                payment_id=payment_id,
            )

            if payment is None:
                raise PaymentNotFoundError

            if payment.status != PaymentStatus.DRAFT:
                raise InvalidPaymentStateTransitionError

            allocations = await self._unit_of_work.payment_allocations.list_by_payment(
                tenant_id=tenant_id,
                payment_id=payment_id,
            )

            if not allocations:
                raise InvalidPaymentStateTransitionError

            allocation_total = sum(
                (allocation.amount for allocation in allocations),
                Decimal("0.00"),
            )

            if allocation_total > payment.amount:
                raise PaymentAllocationExceedsPaymentError

            allocations_by_invoice = {
                allocation.invoice_id: allocation for allocation in allocations
            }

            invoices: dict[UUID, Invoice] = {}

            for invoice_id in sorted(
                allocations_by_invoice,
                key=str,
            ):
                invoice = await self._unit_of_work.invoices.get_by_id_for_update(
                    tenant_id=tenant_id,
                    invoice_id=invoice_id,
                )

                if invoice is None:
                    raise InvalidInvoiceForPaymentError

                invoices[invoice_id] = invoice

            invoices_to_mark_paid: list[Invoice] = []

            for invoice_id, allocation in allocations_by_invoice.items():
                invoice = invoices[invoice_id]

                if invoice.status != InvoiceStatus.ISSUED:
                    raise InvalidInvoiceForPaymentError

                if invoice.currency != payment.currency:
                    raise PaymentCurrencyMismatchError

                posted_total = await self._unit_of_work.payment_allocations.sum_posted_by_invoice(
                    tenant_id=tenant_id,
                    invoice_id=invoice.id,
                )

                new_total = posted_total + allocation.amount

                if new_total > invoice.total_amount:
                    raise PaymentAllocationExceedsInvoiceError

                if new_total == invoice.total_amount:
                    invoices_to_mark_paid.append(invoice)

            if allocation_total < payment.amount:
                raise PaymentNotFullyAllocatedError

            cash_account = await self._get_ledger_account(
                tenant_id=tenant_id,
                purpose=LedgerAccountPurpose.CASH,
            )
            accounts_receivable = await self._get_ledger_account(
                tenant_id=tenant_id,
                purpose=LedgerAccountPurpose.ACCOUNTS_RECEIVABLE,
            )

            now = datetime.now(UTC)

            journal_posting = JournalPostingService(
                accounts=self._unit_of_work.ledger_accounts,
                journal_entries=self._unit_of_work.journal_entries,
                journal_lines=self._unit_of_work.journal_lines,
            )

            await journal_posting.post(
                tenant_id=tenant_id,
                source_type=JournalSourceType.PAYMENT_POSTED.value,
                source_id=payment.id,
                description=f"Payment {payment.payment_number} posted",
                posted_at=now,
                lines=[
                    JournalLineInput(
                        ledger_account_id=cash_account.id,
                        debit=payment.amount,
                        credit=Decimal("0.00"),
                        description=f"Payment {payment.payment_number}",
                    ),
                    JournalLineInput(
                        ledger_account_id=accounts_receivable.id,
                        debit=Decimal("0.00"),
                        credit=payment.amount,
                        description=f"Payment {payment.payment_number}",
                    ),
                ],
            )

            payment.status = PaymentStatus.POSTED
            payment.posted_at = now

            for invoice in invoices_to_mark_paid:
                invoice.status = InvoiceStatus.PAID
                invoice.paid_at = now

            await self._unit_of_work.commit()

            await self._unit_of_work.payments.refresh(payment)

            for invoice in invoices_to_mark_paid:
                await self._unit_of_work.invoices.refresh(invoice)

            return payment

    async def _get_ledger_account(
        self,
        *,
        tenant_id: UUID,
        purpose: LedgerAccountPurpose,
    ) -> LedgerAccount:
        account = await self._unit_of_work.ledger_accounts.get_by_purpose(
            tenant_id,
            purpose.value,
        )

        if account is None:
            raise LedgerAccountNotFoundError(
                f"Ledger account for purpose '{purpose.value}' was not found."
            )

        return account
