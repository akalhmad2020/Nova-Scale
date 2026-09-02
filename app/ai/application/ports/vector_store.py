from typing import Protocol
from uuid import UUID

from app.ai.domain.rag_models import EmbeddedChunk, RetrievedChunk


class VectorStore(Protocol):
    async def replace_document(
        self,
        *,
        tenant_id: UUID,
        document_id: str,
        chunks: tuple[EmbeddedChunk, ...],
    ) -> None: ...

    async def search(
        self,
        *,
        tenant_id: UUID,
        query_embedding: tuple[float, ...],
        limit: int = 5,
    ) -> tuple[RetrievedChunk, ...]: ...
