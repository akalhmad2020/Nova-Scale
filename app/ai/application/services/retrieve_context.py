from collections.abc import Iterable
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
        normalized_query = query.strip()

        if not normalized_query or limit <= 0:
            return ()

        query_embedding = await self._embedding_provider.embed_text(normalized_query)

        retrieved_chunks = await self._vector_store.search(
            tenant_id=tenant_id,
            query_embedding=query_embedding,
            limit=limit,
        )

        relevant_chunks = (
            retrieved_chunk
            for retrieved_chunk in retrieved_chunks
            if retrieved_chunk.score >= self._minimum_score
        )

        return self._deduplicate(
            relevant_chunks,
            limit=limit,
        )

    @staticmethod
    def _deduplicate(
        retrieved_chunks: Iterable[RetrievedChunk],
        *,
        limit: int,
    ) -> tuple[RetrievedChunk, ...]:
        unique_chunks: list[RetrievedChunk] = []
        seen_chunk_ids: set[str] = set()
        seen_content: set[str] = set()

        for retrieved_chunk in retrieved_chunks:
            normalized_content = " ".join(retrieved_chunk.chunk.content.split()).casefold()

            if retrieved_chunk.chunk.id in seen_chunk_ids:
                continue

            if normalized_content in seen_content:
                continue

            seen_chunk_ids.add(retrieved_chunk.chunk.id)
            seen_content.add(normalized_content)
            unique_chunks.append(retrieved_chunk)

            if len(unique_chunks) >= limit:
                break

        return tuple(unique_chunks)
