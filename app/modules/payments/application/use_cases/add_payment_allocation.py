from decimal import Decimal
from uuid import UUID

from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.payments.application.ports.unit_of_work import (
    PaymentsUnitOfWork,
)
from app.modules.payments.domain.enums import PaymentStatus
from app.modules.payments.domain.exceptions import (
    DuplicatePaymentAllocationError,
    InvalidInvoiceForPaymentError,
    InvalidPaymentStateTransitionError,
    PaymentAllocationExceedsInvoiceError,
    PaymentAllocationExceedsPaymentError,
    PaymentCurrencyMismatchError,
    PaymentNotFoundError,
)
from app.modules.payments.infrastructure.models.payment_allocation import (
    PaymentAllocation,
)


class AddPaymentAllocationUseCase:
    def __init__(self, unit_of_work: PaymentsUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
        invoice_id: UUID,
        amount: Decimal,
    ) -> PaymentAllocation:
        async with self._unit_of_work:
            payment = await self._unit_of_work.payments.get_by_id_for_update(
                tenant_id=tenant_id,
                payment_id=payment_id,
            )

            if payment is None:
                raise PaymentNotFoundError

            if payment.status != PaymentStatus.DRAFT:
                raise InvalidPaymentStateTransitionError

            invoice = await self._unit_of_work.invoices.get_by_id(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
            )

            if invoice is None:
                raise InvalidInvoiceForPaymentError

            if invoice.status != InvoiceStatus.ISSUED:
                raise InvalidInvoiceForPaymentError

            if payment.currency != invoice.currency:
                raise PaymentCurrencyMismatchError

            if amount <= Decimal("0"):
                raise ValueError("allocation amount must be greater than zero")

            existing_allocation = (
                await self._unit_of_work.payment_allocations.get_by_payment_and_invoice(
                    tenant_id=tenant_id,
                    payment_id=payment_id,
                    invoice_id=invoice_id,
                )
            )

            if existing_allocation is not None:
                raise DuplicatePaymentAllocationError

            payment_allocations = await self._unit_of_work.payment_allocations.list_by_payment(
                tenant_id=tenant_id,
                payment_id=payment_id,
            )

            payment_allocated_total = sum(
                (allocation.amount for allocation in payment_allocations),
                Decimal("0.00"),
            )

            if payment_allocated_total + amount > payment.amount:
                raise PaymentAllocationExceedsPaymentError

            posted_total = await self._unit_of_work.payment_allocations.sum_posted_by_invoice(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
            )

            if posted_total + amount > invoice.total_amount:
                raise PaymentAllocationExceedsInvoiceError

            allocation = PaymentAllocation(
                tenant_id=tenant_id,
                payment_id=payment_id,
                invoice_id=invoice_id,
                amount=amount,
            )

            await self._unit_of_work.payment_allocations.add(allocation)

            await self._unit_of_work.commit()

            return allocation
