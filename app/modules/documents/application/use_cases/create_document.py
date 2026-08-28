from dataclasses import dataclass
from uuid import UUID

from app.modules.documents.application.exceptions import ShipmentNotFoundError
from app.modules.documents.application.ports.unit_of_work import (
    DocumentsUnitOfWork,
)
from app.modules.documents.domain.enums import DocumentStatus, DocumentType
from app.modules.documents.infrastructure.models.document import Document


@dataclass(frozen=True, slots=True)
class CreateDocumentCommand:
    tenant_id: UUID
    shipment_id: UUID
    document_type: DocumentType
    filename: str
    content_type: str
    storage_key: str
    status: DocumentStatus = DocumentStatus.PENDING


class CreateDocumentUseCase:
    def __init__(
        self,
        unit_of_work: DocumentsUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateDocumentCommand,
    ) -> Document:
        async with self._unit_of_work:
            shipment = await self._unit_of_work.shipments.get_by_id_and_tenant(
                command.shipment_id,
                command.tenant_id,
            )

            if shipment is None:
                raise ShipmentNotFoundError

            document = Document(
                tenant_id=command.tenant_id,
                shipment_id=command.shipment_id,
                type=command.document_type,
                status=command.status,
                filename=command.filename.strip(),
                content_type=command.content_type.strip(),
                storage_key=command.storage_key.strip(),
            )

            self._unit_of_work.documents.add(document)

            await self._unit_of_work.flush()
            await self._unit_of_work.refresh(document)
            await self._unit_of_work.commit()

            return document
