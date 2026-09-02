import pytest

from app.ai.application.services.chunk_text import ChunkTextService
from app.ai.application.services.embed_document import EmbedDocumentService
from tests.unit.ai.fakes import FakeEmbeddingProvider


@pytest.mark.asyncio
async def test_embed_document_chunks_and_embeds_text() -> None:
    embedding_provider = FakeEmbeddingProvider()

    service = EmbedDocumentService(
        chunk_text_service=ChunkTextService(
            chunk_size=30,
            chunk_overlap=5,
        ),
        embedding_provider=embedding_provider,
    )

    embedded_chunks = await service.execute(
        document_id="document-1",
        text=(
            "NovaScale manages shipments and logistics operations. "
            "It also manages billing and payments."
        ),
    )

    assert len(embedded_chunks) > 1
    assert len(embedding_provider.texts) == 1

    embedded_texts = embedding_provider.texts[0]

    assert len(embedded_texts) == len(embedded_chunks)

    for index, embedded_chunk in enumerate(embedded_chunks):
        assert embedded_chunk.chunk.document_id == "document-1"
        assert embedded_chunk.chunk.chunk_index == index
        assert embedded_chunk.embedding == (
            float(index),
            float(index + 1),
        )


@pytest.mark.asyncio
async def test_embed_document_returns_empty_tuple_for_empty_text() -> None:
    embedding_provider = FakeEmbeddingProvider()

    service = EmbedDocumentService(
        chunk_text_service=ChunkTextService(),
        embedding_provider=embedding_provider,
    )

    embedded_chunks = await service.execute(
        document_id="document-1",
        text="",
    )

    assert embedded_chunks == ()
    assert embedding_provider.texts == []
