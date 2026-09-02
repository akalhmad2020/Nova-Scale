from uuid import UUID

from app.ai.application.ports.document_content_reader import (
    DocumentContentReader,
)
from app.ai.application.services.ingest_document import IngestDocumentService


class IndexStoredDocumentService:
    def __init__(
        self,
        *,
        document_content_reader: DocumentContentReader,
        ingest_document_service: IngestDocumentService,
    ) -> None:
        self._document_content_reader = document_content_reader
        self._ingest_document_service = ingest_document_service

    async def execute(
        self,
        *,
        tenant_id: UUID,
        document_id: UUID,
        storage_key: str,
        content_type: str,
    ) -> int:
        text = await self._document_content_reader.read_text(
            storage_key=storage_key,
            content_type=content_type,
        )

        return await self._ingest_document_service.execute(
            tenant_id=tenant_id,
            document_id=str(document_id),
            text=text,
        )
