from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.payments.application.ports.unit_of_work import (
    PaymentsUnitOfWork,
)
from app.modules.payments.domain.enums import PaymentMethod, PaymentStatus
from app.modules.payments.domain.exceptions import (
    DuplicatePaymentNumberError,
    PaymentCustomerNotFoundError,
)
from app.modules.payments.infrastructure.models.payment import Payment


class CreatePaymentUseCase:
    def __init__(self, unit_of_work: PaymentsUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        payment_number: str,
        currency: str,
        amount: Decimal,
        method: PaymentMethod,
        reference: str | None = None,
        received_at: datetime | None = None,
    ) -> Payment:
        normalized_payment_number = payment_number.strip()
        normalized_currency = currency.strip().upper()

        normalized_reference = (
            reference.strip() if reference is not None and reference.strip() else None
        )

        async with self._unit_of_work:
            customer = await self._unit_of_work.customers.get_by_id_and_tenant(
                customer_id,
                tenant_id,
            )

            if customer is None:
                raise PaymentCustomerNotFoundError

            existing_payment = await self._unit_of_work.payments.get_by_number(
                tenant_id=tenant_id,
                payment_number=normalized_payment_number,
            )

            if existing_payment is not None:
                raise DuplicatePaymentNumberError

            payment = Payment(
                tenant_id=tenant_id,
                customer_id=customer_id,
                payment_number=normalized_payment_number,
                status=PaymentStatus.DRAFT,
                currency=normalized_currency,
                amount=amount,
                method=method,
                reference=normalized_reference,
                received_at=received_at,
                posted_at=None,
            )

            await self._unit_of_work.payments.add(payment)

            await self._unit_of_work.commit()
            await self._unit_of_work.payments.refresh(payment)

            return payment
