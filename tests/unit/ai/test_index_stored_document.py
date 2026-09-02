from uuid import uuid4

import pytest

from app.ai.application.services.chunk_text import ChunkTextService
from app.ai.application.services.embed_document import EmbedDocumentService
from app.ai.application.services.index_stored_document import (
    IndexStoredDocumentService,
)
from app.ai.application.services.ingest_document import IngestDocumentService
from tests.unit.ai.fakes import FakeEmbeddingProvider, FakeVectorStore


class FakeDocumentContentReader:
    def __init__(self, text: str) -> None:
        self._text = text
        self.reads: list[tuple[str, str]] = []

    async def read_text(
        self,
        *,
        storage_key: str,
        content_type: str,
    ) -> str:
        self.reads.append(
            (
                storage_key,
                content_type,
            )
        )

        return self._text


@pytest.mark.asyncio
async def test_index_stored_document_reads_and_ingests_document() -> None:
    tenant_id = uuid4()
    document_id = uuid4()

    content_reader = FakeDocumentContentReader("Shipment NOVA-100 is in transit.")
    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()

    embed_document_service = EmbedDocumentService(
        chunk_text_service=ChunkTextService(),
        embedding_provider=embedding_provider,
    )

    ingest_document_service = IngestDocumentService(
        embed_document_service=embed_document_service,
        vector_store=vector_store,
    )

    service = IndexStoredDocumentService(
        document_content_reader=content_reader,
        ingest_document_service=ingest_document_service,
    )

    count = await service.execute(
        tenant_id=tenant_id,
        document_id=document_id,
        storage_key="documents/shipping-label.pdf",
        content_type="application/pdf",
    )

    assert count == 1

    assert content_reader.reads == [
        (
            "documents/shipping-label.pdf",
            "application/pdf",
        )
    ]

    assert len(vector_store.replaced_documents) == 1

    stored_tenant_id, stored_document_id, chunks = vector_store.replaced_documents[0]

    assert stored_tenant_id == tenant_id
    assert stored_document_id == str(document_id)

    assert len(chunks) == 1
    assert chunks[0].chunk.document_id == str(document_id)
    assert chunks[0].chunk.content == "Shipment NOVA-100 is in transit."


@pytest.mark.asyncio
async def test_index_stored_document_clears_index_for_blank_content() -> None:
    tenant_id = uuid4()
    document_id = uuid4()

    content_reader = FakeDocumentContentReader("   ")
    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()

    embed_document_service = EmbedDocumentService(
        chunk_text_service=ChunkTextService(),
        embedding_provider=embedding_provider,
    )

    ingest_document_service = IngestDocumentService(
        embed_document_service=embed_document_service,
        vector_store=vector_store,
    )

    service = IndexStoredDocumentService(
        document_content_reader=content_reader,
        ingest_document_service=ingest_document_service,
    )

    count = await service.execute(
        tenant_id=tenant_id,
        document_id=document_id,
        storage_key="documents/empty.txt",
        content_type="text/plain",
    )

    assert count == 0
    assert vector_store.replaced_documents == [
        (
            tenant_id,
            str(document_id),
            (),
        )
    ]
