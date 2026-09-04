from collections.abc import Sequence
from uuid import UUID

from app.modules.billing.application.exceptions import (
    InvoiceNotFoundError,
)
from app.modules.billing.application.ports.unit_of_work import (
    BillingUnitOfWork,
)
from app.modules.billing.infrastructure.models.invoice_line import InvoiceLine


class ListInvoiceLinesUseCase:
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
    ) -> Sequence[InvoiceLine]:
        async with self._unit_of_work:
            invoice = await self._unit_of_work.invoices.get_by_id(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
            )

            if invoice is None:
                raise InvoiceNotFoundError("Invoice was not found.")

            return await self._unit_of_work.invoice_lines.list_by_invoice(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
            )
