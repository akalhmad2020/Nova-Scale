from uuid import UUID

from app.ai.application.ports.vector_store import VectorStore
from app.ai.application.services.embed_document import EmbedDocumentService


class IngestDocumentService:
    def __init__(
        self,
        *,
        embed_document_service: EmbedDocumentService,
        vector_store: VectorStore,
    ) -> None:
        self._embed_document_service = embed_document_service
        self._vector_store = vector_store

    async def execute(
        self,
        *,
        tenant_id: UUID,
        document_id: str,
        text: str,
    ) -> int:
        embedded_chunks = await self._embed_document_service.execute(
            document_id=document_id,
            text=text,
        )

        await self._vector_store.replace_document(
            tenant_id=tenant_id,
            document_id=document_id,
            chunks=embedded_chunks,
        )

        return len(embedded_chunks)
