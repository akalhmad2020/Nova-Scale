from typing import Protocol
from uuid import UUID

from app.modules.payments.infrastructure.models.payment import Payment


class PaymentRepository(Protocol):
    async def add(self, payment: Payment) -> None: ...

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
    ) -> Payment | None: ...

    async def get_by_number(
        self,
        *,
        tenant_id: UUID,
        payment_number: str,
    ) -> Payment | None: ...

    async def list_by_tenant(
        self,
        *,
        tenant_id: UUID,
    ) -> list[Payment]: ...

    async def refresh(self, payment: Payment) -> None: ...

    async def get_by_id_for_update(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
    ) -> Payment | None: ...
