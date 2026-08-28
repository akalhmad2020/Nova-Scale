from dataclasses import dataclass
from uuid import UUID

from app.modules.documents.application.ports.unit_of_work import (
    DocumentsUnitOfWork,
)
from app.modules.documents.infrastructure.models.document import Document


@dataclass(frozen=True, slots=True)
class ListShipmentDocumentsQuery:
    tenant_id: UUID
    shipment_id: UUID


class ListShipmentDocumentsUseCase:
    def __init__(
        self,
        unit_of_work: DocumentsUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: ListShipmentDocumentsQuery,
    ) -> list[Document]:
        async with self._unit_of_work:
            return await self._unit_of_work.documents.list_by_shipment(
                query.shipment_id,
                query.tenant_id,
            )
