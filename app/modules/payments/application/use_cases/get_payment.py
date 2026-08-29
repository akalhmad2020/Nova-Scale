from uuid import UUID

from app.modules.payments.application.ports.unit_of_work import (
    PaymentsUnitOfWork,
)
from app.modules.payments.domain.exceptions import PaymentNotFoundError
from app.modules.payments.infrastructure.models.payment import Payment


class GetPaymentUseCase:
    def __init__(self, unit_of_work: PaymentsUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
    ) -> Payment:
        async with self._unit_of_work:
            payment = await self._unit_of_work.payments.get_by_id(
                tenant_id=tenant_id,
                payment_id=payment_id,
            )

            if payment is None:
                raise PaymentNotFoundError

            return payment
