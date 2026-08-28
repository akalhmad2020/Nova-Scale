from typing import Protocol
from uuid import UUID

from app.modules.documents.infrastructure.models.document import Document


class DocumentRepository(Protocol):
    async def get_by_id_and_tenant(
        self,
        document_id: UUID,
        tenant_id: UUID,
    ) -> Document | None: ...

    async def list_by_shipment(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> list[Document]: ...

    def add(
        self,
        document: Document,
    ) -> None: ...
