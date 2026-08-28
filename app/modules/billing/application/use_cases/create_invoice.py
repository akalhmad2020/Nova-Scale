from decimal import Decimal
from uuid import UUID

from app.modules.billing.application.exceptions import (
    CustomerNotFoundError,
    InvalidInvoiceAmountError,
    InvoiceNumberAlreadyExistsError,
)
from app.modules.billing.application.ports.unit_of_work import BillingUnitOfWork
from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.domain.money import calculate_invoice_total, round_money
from app.modules.billing.infrastructure.models.invoice import Invoice


class CreateInvoiceUseCase:
    def __init__(
        self,
        unit_of_work: BillingUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        invoice_number: str,
        currency: str,
        tax_amount: Decimal = Decimal("0.00"),
    ) -> Invoice:
        invoice_number = invoice_number.strip()
        currency = currency.strip().upper()
        tax_amount = round_money(tax_amount)

        if tax_amount < Decimal("0.00"):
            raise InvalidInvoiceAmountError("Tax amount cannot be negative")

        async with self._unit_of_work as unit_of_work:
            customer = await unit_of_work.customers.get_by_id_and_tenant(
                customer_id,
                tenant_id,
            )

            if customer is None:
                raise CustomerNotFoundError

            existing_invoice = await unit_of_work.invoices.get_by_number(
                tenant_id=tenant_id,
                invoice_number=invoice_number,
            )

            if existing_invoice is not None:
                raise InvoiceNumberAlreadyExistsError

            subtotal = Decimal("0.00")

            invoice = Invoice(
                tenant_id=tenant_id,
                customer_id=customer_id,
                invoice_number=invoice_number,
                status=InvoiceStatus.DRAFT,
                currency=currency,
                subtotal=subtotal,
                tax_amount=tax_amount,
                total_amount=calculate_invoice_total(
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                ),
            )

            await unit_of_work.invoices.add(invoice)

            await unit_of_work.commit()

            return invoice
