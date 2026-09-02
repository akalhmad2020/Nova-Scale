from uuid import UUID

from app.ai.application.ports.embedding_provider import EmbeddingProvider
from app.ai.application.ports.vector_store import VectorStore
from app.ai.domain.rag_models import RetrievedChunk


class RetrieveContextService:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        minimum_score: float = 0.5,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._minimum_score = minimum_score

    async def execute(
        self,
        *,
        tenant_id: UUID,
        query: str,
        limit: int = 5,
    ) -> tuple[RetrievedChunk, ...]:
        if not query.strip():
            return ()

        query_embedding = await self._embedding_provider.embed_text(query)

        retrieved_chunks = await self._vector_store.search(
            tenant_id=tenant_id,
            query_embedding=query_embedding,
            limit=limit,
        )

        return tuple(
            retrieved_chunk
            for retrieved_chunk in retrieved_chunks
            if retrieved_chunk.score >= self._minimum_score
        )
