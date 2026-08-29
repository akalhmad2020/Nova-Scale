from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.billing.infrastructure.models.invoice import Invoice


class InvoiceRepository(Protocol):
    async def add(self, invoice: Invoice) -> None: ...

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Invoice | None: ...

    async def get_by_id_for_update(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Invoice | None: ...

    async def get_by_number(
        self,
        *,
        tenant_id: UUID,
        invoice_number: str,
    ) -> Invoice | None: ...

    async def list_by_tenant(
        self,
        *,
        tenant_id: UUID,
    ) -> Sequence[Invoice]: ...

    async def refresh(self, invoice: Invoice) -> None: ...
