from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.ports.vector_store import VectorStore
from app.ai.domain.rag_models import DocumentChunk, EmbeddedChunk, RetrievedChunk
from app.ai.infrastructure.vector_store.models import RagChunkModel


class PostgresVectorStore(VectorStore):
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def replace_document(
        self,
        *,
        tenant_id: UUID,
        document_id: str,
        chunks: tuple[EmbeddedChunk, ...],
    ) -> None:
        await self._session.execute(
            delete(RagChunkModel).where(
                RagChunkModel.tenant_id == tenant_id,
                RagChunkModel.document_id == document_id,
            )
        )

        if not chunks:
            await self._session.flush()
            return

        statement = insert(RagChunkModel).values(
            [
                {
                    "id": embedded_chunk.chunk.id,
                    "tenant_id": tenant_id,
                    "document_id": embedded_chunk.chunk.document_id,
                    "chunk_index": embedded_chunk.chunk.chunk_index,
                    "content": embedded_chunk.chunk.content,
                    "embedding": list(embedded_chunk.embedding),
                }
                for embedded_chunk in chunks
            ]
        )

        await self._session.execute(statement)
        await self._session.flush()

    async def search(
        self,
        *,
        tenant_id: UUID,
        query_embedding: tuple[float, ...],
        limit: int = 5,
    ) -> tuple[RetrievedChunk, ...]:
        if limit <= 0:
            return ()

        distance = RagChunkModel.embedding.cosine_distance(list(query_embedding))

        statement = (
            select(
                RagChunkModel,
                distance.label("distance"),
            )
            .where(
                RagChunkModel.tenant_id == tenant_id,
            )
            .order_by(distance)
            .limit(limit)
        )

        result = await self._session.execute(statement)

        rows = result.all()

        return tuple(
            RetrievedChunk(
                chunk=DocumentChunk(
                    id=model.id,
                    document_id=model.document_id,
                    content=model.content,
                    chunk_index=model.chunk_index,
                ),
                score=1.0 - float(vector_distance),
            )
            for model, vector_distance in rows
        )
