from app.ai.application.ports.embedding_provider import EmbeddingProvider
from app.ai.application.services.chunk_text import ChunkTextService
from app.ai.domain.rag_models import EmbeddedChunk


class EmbedDocumentService:
    def __init__(
        self,
        *,
        chunk_text_service: ChunkTextService,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._chunk_text_service = chunk_text_service
        self._embedding_provider = embedding_provider

    async def execute(
        self,
        *,
        document_id: str,
        text: str,
    ) -> tuple[EmbeddedChunk, ...]:
        chunks = self._chunk_text_service.execute(
            document_id=document_id,
            text=text,
        )

        if not chunks:
            return ()

        embeddings = await self._embedding_provider.embed_texts(
            tuple(chunk.content for chunk in chunks),
        )

        if len(embeddings) != len(chunks):
            raise RuntimeError(
                "Embedding provider returned a different number of embeddings than document chunks"
            )

        return tuple(
            EmbeddedChunk(
                chunk=chunk,
                embedding=embedding,
            )
            for chunk, embedding in zip(
                chunks,
                embeddings,
                strict=True,
            )
        )
