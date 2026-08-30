from uuid import UUID

from app.modules.audit.application.contracts import AuditRecord
from app.modules.audit.application.use_cases.record_audit_log import (
    RecordAuditLogUseCase,
)
from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.billing.application.exceptions import (
    InvalidInvoiceStateTransitionError,
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
            invoice = await self._unit_of_work.invoices.get_by_id(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
            )

            if invoice is None:
                raise InvoiceNotFoundError("Invoice was not found.")

            if not can_transition_invoice_status(
                InvoiceStatus(invoice.status),
                InvoiceStatus.VOID,
            ):
                raise InvalidInvoiceStateTransitionError(
                    "Invoice cannot be voided from its current state."
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
                    },
                )
            )

            await self._unit_of_work.commit()
            await self._unit_of_work.invoices.refresh(invoice)

            return invoice
