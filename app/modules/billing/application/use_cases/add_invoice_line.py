from decimal import Decimal
from uuid import UUID

from app.modules.billing.application.exceptions import (
    InvalidInvoiceAmountError,
    InvoiceNotEditableError,
    InvoiceNotFoundError,
    ShipmentNotFoundError,
)
from app.modules.billing.application.ports.unit_of_work import BillingUnitOfWork
from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.domain.money import (
    calculate_invoice_total,
    calculate_line_amount,
    calculate_subtotal,
)
from app.modules.billing.infrastructure.models.invoice_line import InvoiceLine


class AddInvoiceLineUseCase:
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
        description: str,
        quantity: Decimal,
        unit_price: Decimal,
        shipment_id: UUID | None = None,
    ) -> InvoiceLine:
        description = description.strip()

        if quantity <= Decimal("0"):
            raise InvalidInvoiceAmountError("Quantity must be greater than zero")

        if unit_price < Decimal("0"):
            raise InvalidInvoiceAmountError("Unit price cannot be negative")

        async with self._unit_of_work as unit_of_work:
            invoice = await unit_of_work.invoices.get_by_id(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
            )

            if invoice is None:
                raise InvoiceNotFoundError

            if invoice.status != InvoiceStatus.DRAFT:
                raise InvoiceNotEditableError

            if shipment_id is not None:
                shipment = await unit_of_work.shipments.get_by_id_and_tenant(
                    shipment_id,
                    tenant_id,
                )

                if shipment is None:
                    raise ShipmentNotFoundError

            amount = calculate_line_amount(
                quantity=quantity,
                unit_price=unit_price,
            )

            invoice_line = InvoiceLine(
                tenant_id=tenant_id,
                invoice_id=invoice.id,
                shipment_id=shipment_id,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                amount=amount,
            )

            await unit_of_work.invoice_lines.add(invoice_line)

            lines = await unit_of_work.invoice_lines.list_by_invoice(
                tenant_id=tenant_id,
                invoice_id=invoice.id,
            )

            invoice.subtotal = calculate_subtotal(line.amount for line in lines)

            invoice.total_amount = calculate_invoice_total(
                subtotal=invoice.subtotal,
                tax_amount=invoice.tax_amount,
            )

            await unit_of_work.commit()

            return invoice_line
