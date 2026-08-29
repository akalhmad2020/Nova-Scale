from uuid import UUID

from app.modules.payments.application.ports.unit_of_work import (
    PaymentsUnitOfWork,
)
from app.modules.payments.domain.enums import PaymentStatus
from app.modules.payments.domain.exceptions import (
    InvalidPaymentStateTransitionError,
    PaymentAllocationNotFoundError,
    PaymentNotFoundError,
)


class RemovePaymentAllocationUseCase:
    def __init__(self, unit_of_work: PaymentsUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
        payment_allocation_id: UUID,
    ) -> None:
        async with self._unit_of_work:
            payment = await self._unit_of_work.payments.get_by_id_for_update(
                tenant_id=tenant_id,
                payment_id=payment_id,
            )

            if payment is None:
                raise PaymentNotFoundError

            if payment.status != PaymentStatus.DRAFT:
                raise InvalidPaymentStateTransitionError

            allocation = await self._unit_of_work.payment_allocations.get_by_id(
                tenant_id=tenant_id,
                payment_allocation_id=payment_allocation_id,
            )

            if allocation is None or allocation.payment_id != payment_id:
                raise PaymentAllocationNotFoundError

            await self._unit_of_work.payment_allocations.delete(allocation)

            await self._unit_of_work.commit()
