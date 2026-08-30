from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.modules.billing.application.exceptions import (
    InvalidInvoiceStateTransitionError,
    InvoiceHasNoLinesError,
    InvoiceNotFoundError,
)
from app.modules.billing.application.ports.unit_of_work import (
    BillingUnitOfWork,
)
from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.domain.lifecycle import (
    can_transition_invoice_status,
)
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.ledger.application.exceptions import (
    LedgerAccountInactiveError,
    LedgerAccountNotFoundError,
)
from app.modules.ledger.application.services import (
    JournalLineInput,
    JournalPostingService,
)
from app.modules.ledger.domain.enums import (
    JournalSourceType,
    LedgerAccountPurpose,
    LedgerAccountStatus,
)
from app.modules.ledger.infrastructure.models import LedgerAccount
from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)

INVOICE_ISSUED_EVENT_TYPE = "invoice.issued"


class IssueInvoiceUseCase:
    def __init__(
        self,
        unit_of_work: BillingUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Invoice:
        async with self._unit_of_work:
            invoice = await self._unit_of_work.invoices.get_by_id_for_update(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
            )

            if invoice is None:
                raise InvoiceNotFoundError("Invoice was not found.")

            if not can_transition_invoice_status(
                InvoiceStatus(invoice.status),
                InvoiceStatus.ISSUED,
            ):
                raise InvalidInvoiceStateTransitionError(
                    "Invoice cannot be issued from its current state."
                )

            lines = await self._unit_of_work.invoice_lines.list_by_invoice(
                tenant_id=tenant_id,
                invoice_id=invoice.id,
            )

            if not lines:
                raise InvoiceHasNoLinesError(
                    "Invoice must contain at least one line before issuing."
                )

            accounts_receivable = await self._get_active_ledger_account(
                tenant_id=tenant_id,
                purpose=LedgerAccountPurpose.ACCOUNTS_RECEIVABLE,
            )

            revenue = await self._get_active_ledger_account(
                tenant_id=tenant_id,
                purpose=LedgerAccountPurpose.REVENUE,
            )

            tax_payable: LedgerAccount | None = None

            if invoice.tax_amount > Decimal("0.00"):
                tax_payable = await self._get_active_ledger_account(
                    tenant_id=tenant_id,
                    purpose=LedgerAccountPurpose.TAX_PAYABLE,
                )

            issued_at = datetime.now(UTC)

            journal_lines = [
                JournalLineInput(
                    ledger_account_id=accounts_receivable.id,
                    debit=invoice.total_amount,
                    credit=Decimal("0.00"),
                    description=f"Invoice {invoice.invoice_number}",
                ),
                JournalLineInput(
                    ledger_account_id=revenue.id,
                    debit=Decimal("0.00"),
                    credit=invoice.subtotal,
                    description=f"Invoice {invoice.invoice_number}",
                ),
            ]

            if tax_payable is not None:
                journal_lines.append(
                    JournalLineInput(
                        ledger_account_id=tax_payable.id,
                        debit=Decimal("0.00"),
                        credit=invoice.tax_amount,
                        description=f"Invoice {invoice.invoice_number} tax",
                    )
                )

            journal_posting = JournalPostingService(
                accounts=self._unit_of_work.ledger_accounts,
                journal_entries=self._unit_of_work.journal_entries,
                journal_lines=self._unit_of_work.journal_lines,
            )

            await journal_posting.post(
                tenant_id=tenant_id,
                source_type=JournalSourceType.INVOICE_ISSUED.value,
                source_id=invoice.id,
                description=f"Invoice {invoice.invoice_number} issued",
                posted_at=issued_at,
                lines=journal_lines,
            )

            invoice.status = InvoiceStatus.ISSUED
            invoice.issued_at = issued_at

            outbox_message = OutboxMessage(
                tenant_id=tenant_id,
                event_type=INVOICE_ISSUED_EVENT_TYPE,
                payload={
                    "invoice_id": str(invoice.id),
                    "customer_id": str(invoice.customer_id),
                    "invoice_number": invoice.invoice_number,
                    "currency": invoice.currency,
                    "subtotal": str(invoice.subtotal),
                    "tax_amount": str(invoice.tax_amount),
                    "total_amount": str(invoice.total_amount),
                    "issued_at": issued_at.isoformat(),
                },
                status=OutboxMessageStatus.PENDING.value,
                attempt_count=0,
                available_at=None,
                claim_token=None,
                lease_expires_at=None,
                processed_at=None,
                last_error=None,
            )

            await self._unit_of_work.outbox_messages.add(
                outbox_message,
            )

            await self._unit_of_work.commit()
            await self._unit_of_work.invoices.refresh(invoice)

            return invoice

    async def _get_active_ledger_account(
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

        if account.status != LedgerAccountStatus.ACTIVE.value:
            raise LedgerAccountInactiveError(
                f"Ledger account for purpose '{purpose.value}' is inactive."
            )

        return account
