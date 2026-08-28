from uuid import UUID

from app.modules.billing.application.exceptions import (
    InvoiceLineNotFoundError,
    InvoiceNotEditableError,
    InvoiceNotFoundError,
)
from app.modules.billing.application.ports.unit_of_work import (
    BillingUnitOfWork,
)
from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.domain.money import (
    calculate_invoice_total,
    calculate_subtotal,
)


class RemoveInvoiceLineUseCase:
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
        invoice_line_id: UUID,
    ) -> None:
        async with self._unit_of_work:
            invoice = await self._unit_of_work.invoices.get_by_id(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
            )

            if invoice is None:
                raise InvoiceNotFoundError("Invoice was not found.")

            if invoice.status != InvoiceStatus.DRAFT:
                raise InvoiceNotEditableError("Only draft invoices can be modified.")

            invoice_line = await self._unit_of_work.invoice_lines.get_by_id(
                tenant_id=tenant_id,
                invoice_line_id=invoice_line_id,
            )

            if invoice_line is None or invoice_line.invoice_id != invoice.id:
                raise InvoiceLineNotFoundError("Invoice line was not found.")

            await self._unit_of_work.invoice_lines.delete(invoice_line)

            lines = await self._unit_of_work.invoice_lines.list_by_invoice(
                tenant_id=tenant_id,
                invoice_id=invoice.id,
            )

            remaining_amounts = (line.amount for line in lines if line.id != invoice_line.id)

            invoice.subtotal = calculate_subtotal(remaining_amounts)
            invoice.total_amount = calculate_invoice_total(
                subtotal=invoice.subtotal,
                tax_amount=invoice.tax_amount,
            )

            await self._unit_of_work.commit()
