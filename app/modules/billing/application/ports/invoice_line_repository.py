from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.billing.infrastructure.models.invoice_line import InvoiceLine


class InvoiceLineRepository(Protocol):
    async def add(self, invoice_line: InvoiceLine) -> None: ...

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        invoice_line_id: UUID,
    ) -> InvoiceLine | None: ...

    async def list_by_invoice(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Sequence[InvoiceLine]: ...

    async def delete(self, invoice_line: InvoiceLine) -> None: ...
