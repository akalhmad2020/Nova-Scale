from collections.abc import Sequence
from uuid import UUID

from app.modules.billing.application.ports.unit_of_work import (
    BillingUnitOfWork,
)
from app.modules.billing.infrastructure.models.invoice import Invoice


class ListInvoicesUseCase:
    def __init__(
        self,
        unit_of_work: BillingUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        tenant_id: UUID,
    ) -> Sequence[Invoice]:
        async with self._unit_of_work:
            return await self._unit_of_work.invoices.list_by_tenant(
                tenant_id=tenant_id,
            )
