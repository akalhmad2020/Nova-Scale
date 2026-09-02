from uuid import uuid4

import pytest

from app.ai.application.services.chunk_text import ChunkTextService
from app.ai.application.services.embed_document import EmbedDocumentService
from app.ai.application.services.ingest_document import IngestDocumentService
from tests.unit.ai.fakes import FakeEmbeddingProvider, FakeVectorStore


@pytest.mark.asyncio
async def test_ingest_document_embeds_and_stores_chunks() -> None:
    tenant_id = uuid4()
    document_id = "document-1"

    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()

    embed_document_service = EmbedDocumentService(
        chunk_text_service=ChunkTextService(
            chunk_size=30,
            chunk_overlap=5,
        ),
        embedding_provider=embedding_provider,
    )

    service = IngestDocumentService(
        embed_document_service=embed_document_service,
        vector_store=vector_store,
    )

    chunk_count = await service.execute(
        tenant_id=tenant_id,
        document_id=document_id,
        text=(
            "NovaScale manages shipments and logistics operations. "
            "It also manages billing and payments."
        ),
    )

    assert chunk_count > 1
    assert len(vector_store.replaced_documents) == 1

    stored_tenant_id, stored_document_id, stored_chunks = vector_store.replaced_documents[0]

    assert stored_tenant_id == tenant_id
    assert stored_document_id == document_id
    assert len(stored_chunks) == chunk_count

    assert all(chunk.chunk.document_id == document_id for chunk in stored_chunks)


@pytest.mark.asyncio
async def test_ingest_document_does_not_store_empty_document() -> None:
    tenant_id = uuid4()

    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()

    embed_document_service = EmbedDocumentService(
        chunk_text_service=ChunkTextService(),
        embedding_provider=embedding_provider,
    )

    service = IngestDocumentService(
        embed_document_service=embed_document_service,
        vector_store=vector_store,
    )

    chunk_count = await service.execute(
        tenant_id=tenant_id,
        document_id="document-1",
        text="",
    )

    assert chunk_count == 0
    assert vector_store.replaced_documents == [
        (
            tenant_id,
            "document-1",
            (),
        )
    ]
