from uuid import UUID

from app.modules.payments.application.ports.unit_of_work import (
    PaymentsUnitOfWork,
)
from app.modules.payments.infrastructure.models.payment import Payment


class ListPaymentsUseCase:
    def __init__(self, unit_of_work: PaymentsUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        tenant_id: UUID,
    ) -> list[Payment]:
        async with self._unit_of_work:
            payments = await self._unit_of_work.payments.list_by_tenant(
                tenant_id=tenant_id,
            )

            return list(payments)
