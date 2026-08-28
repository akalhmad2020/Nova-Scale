from dataclasses import dataclass
from uuid import UUID

from app.modules.documents.application.exceptions import (
    DocumentNotFoundError,
    InvalidDocumentStateTransitionError,
)
from app.modules.documents.application.ports.unit_of_work import (
    DocumentsUnitOfWork,
)
from app.modules.documents.domain.enums import DocumentStatus
from app.modules.documents.infrastructure.models.document import Document


@dataclass(frozen=True, slots=True)
class MarkDocumentFailedCommand:
    tenant_id: UUID
    document_id: UUID


class MarkDocumentFailedUseCase:
    def __init__(
        self,
        unit_of_work: DocumentsUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: MarkDocumentFailedCommand,
    ) -> Document:
        async with self._unit_of_work:
            document = await self._unit_of_work.documents.get_by_id_and_tenant(
                command.document_id,
                command.tenant_id,
            )

            if document is None:
                raise DocumentNotFoundError

            if document.status != DocumentStatus.PENDING:
                raise InvalidDocumentStateTransitionError

            document.status = DocumentStatus.FAILED

            await self._unit_of_work.flush()
            await self._unit_of_work.refresh(document)
            await self._unit_of_work.commit()

            return document
