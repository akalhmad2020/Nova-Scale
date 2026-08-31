from datetime import UTC, datetime
from uuid import UUID

from app.modules.audit.application.contracts import AuditRecord
from app.modules.audit.application.use_cases.record_audit_log import (
    RecordAuditLogUseCase,
)
from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.billing.application.exceptions import (
    InvalidInvoiceStateTransitionError,
    InvoiceLedgerEntryNotFoundError,
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
from app.modules.ledger.application.services import (
    JournalLineInput,
    JournalPostingService,
)
from app.modules.ledger.domain.enums import JournalSourceType


class VoidInvoiceUseCase:
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
        actor_id: UUID,
    ) -> Invoice:
        async with self._unit_of_work:
            invoice = await self._unit_of_work.invoices.get_by_id_for_update(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
            )

            if invoice is None:
                raise InvoiceNotFoundError("Invoice was not found.")

            current_status = InvoiceStatus(invoice.status)

            if not can_transition_invoice_status(
                current_status,
                InvoiceStatus.VOID,
            ):
                raise InvalidInvoiceStateTransitionError(
                    "Invoice cannot be voided from its current state."
                )

            voided_at = datetime.now(UTC)

            if current_status == InvoiceStatus.ISSUED:
                await self._reverse_issued_invoice(
                    tenant_id=tenant_id,
                    invoice=invoice,
                    voided_at=voided_at,
                )

            invoice.status = InvoiceStatus.VOID

            audit = RecordAuditLogUseCase(
                audit_logs=self._unit_of_work.audit_logs,
            )

            await audit.execute(
                AuditRecord(
                    tenant_id=tenant_id,
                    actor_type=AuditActorType.USER,
                    actor_id=actor_id,
                    action="invoice.voided",
                    resource_type="invoice",
                    resource_id=invoice.id,
                    outcome=AuditOutcome.SUCCESS,
                    metadata={
                        "invoice_number": invoice.invoice_number,
                        "customer_id": str(invoice.customer_id),
                        "currency": invoice.currency,
                        "subtotal": str(invoice.subtotal),
                        "tax_amount": str(invoice.tax_amount),
                        "total_amount": str(invoice.total_amount),
                        "previous_status": current_status.value,
                    },
                    occurred_at=voided_at,
                )
            )

            await self._unit_of_work.commit()
            await self._unit_of_work.invoices.refresh(invoice)

            return invoice

    async def _reverse_issued_invoice(
        self,
        *,
        tenant_id: UUID,
        invoice: Invoice,
        voided_at: datetime,
    ) -> None:
        issued_journal = await self._unit_of_work.journal_entries.get_by_source(
            tenant_id,
            JournalSourceType.INVOICE_ISSUED.value,
            invoice.id,
        )

        if issued_journal is None:
            raise InvoiceLedgerEntryNotFoundError("Issued invoice ledger entry was not found.")

        issued_lines = await self._unit_of_work.journal_lines.list_by_entry(
            tenant_id,
            issued_journal.id,
        )

        if not issued_lines:
            raise InvoiceLedgerEntryNotFoundError("Issued invoice ledger lines were not found.")

        reversal_lines = [
            JournalLineInput(
                ledger_account_id=line.ledger_account_id,
                debit=line.credit,
                credit=line.debit,
                description=(f"Reversal of invoice {invoice.invoice_number}"),
            )
            for line in issued_lines
        ]

        journal_posting = JournalPostingService(
            accounts=self._unit_of_work.ledger_accounts,
            journal_entries=self._unit_of_work.journal_entries,
            journal_lines=self._unit_of_work.journal_lines,
        )

        await journal_posting.post(
            tenant_id=tenant_id,
            source_type=JournalSourceType.INVOICE_VOIDED.value,
            source_id=invoice.id,
            description=f"Invoice {invoice.invoice_number} voided",
            posted_at=voided_at,
            lines=reversal_lines,
            allow_inactive_accounts=True,
        )
