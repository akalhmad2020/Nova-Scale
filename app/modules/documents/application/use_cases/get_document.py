from dataclasses import dataclass
from uuid import UUID

from app.modules.documents.application.exceptions import DocumentNotFoundError
from app.modules.documents.application.ports.unit_of_work import (
    DocumentsUnitOfWork,
)
from app.modules.documents.infrastructure.models.document import Document


@dataclass(frozen=True, slots=True)
class GetDocumentQuery:
    tenant_id: UUID
    document_id: UUID


class GetDocumentUseCase:
    def __init__(
        self,
        unit_of_work: DocumentsUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetDocumentQuery,
    ) -> Document:
        async with self._unit_of_work:
            document = await self._unit_of_work.documents.get_by_id_and_tenant(
                query.document_id,
                query.tenant_id,
            )

            if document is None:
                raise DocumentNotFoundError

            return document
