from datetime import UTC, datetime
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
            invoice = await self._unit_of_work.invoices.get_by_id(
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

            invoice.status = InvoiceStatus.ISSUED
            invoice.issued_at = datetime.now(UTC)

            await self._unit_of_work.commit()
            await self._unit_of_work.invoices.refresh(invoice)
            return invoice
