from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.services.chunk_text import ChunkTextService
from app.ai.application.services.embed_document import EmbedDocumentService
from app.ai.application.services.index_stored_document import (
    IndexStoredDocumentService,
)
from app.ai.application.services.ingest_document import IngestDocumentService
from app.ai.application.services.retrieve_context import RetrieveContextService
from app.ai.infrastructure.dependencies import build_embedding_provider
from app.ai.infrastructure.document_content.local_text_reader import (
    LocalTextDocumentContentReader,
)
from app.ai.infrastructure.vector_store.postgres_vector_store import (
    PostgresVectorStore,
)
from app.core.config import get_settings


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stored_document_can_be_indexed_and_retrieved(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    tenant_id = uuid4()
    document_id = uuid4()

    storage_root = tmp_path / "storage"
    document_directory = storage_root / "documents"
    document_directory.mkdir(parents=True)

    storage_key = f"documents/{document_id}.txt"

    document_path = storage_root / storage_key
    document_path.write_text(
        (
            "Shipment NOVA-200 is currently waiting for customs clearance. "
            "The shipment has reached the border facility and is pending "
            "customs inspection."
        ),
        encoding="utf-8",
    )

    settings = get_settings()

    embedding_provider = build_embedding_provider(settings)

    vector_store = PostgresVectorStore(
        session=db_session,
    )

    document_content_reader = LocalTextDocumentContentReader(
        storage_root=storage_root,
    )

    chunk_text_service = ChunkTextService(
        chunk_size=1000,
        chunk_overlap=150,
    )

    embed_document_service = EmbedDocumentService(
        chunk_text_service=chunk_text_service,
        embedding_provider=embedding_provider,
    )

    ingest_document_service = IngestDocumentService(
        embed_document_service=embed_document_service,
        vector_store=vector_store,
    )

    index_stored_document_service = IndexStoredDocumentService(
        document_content_reader=document_content_reader,
        ingest_document_service=ingest_document_service,
    )

    retrieve_context_service = RetrieveContextService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    indexed_chunks = await index_stored_document_service.execute(
        tenant_id=tenant_id,
        document_id=document_id,
        storage_key=storage_key,
        content_type="text/plain",
    )

    assert indexed_chunks > 0

    retrieved_chunks = await retrieve_context_service.execute(
        tenant_id=tenant_id,
        query="What is happening with shipment NOVA-200?",
        limit=5,
    )

    assert retrieved_chunks

    retrieved_document_ids = {chunk.chunk.document_id for chunk in retrieved_chunks}

    assert str(document_id) in retrieved_document_ids

    document_chunks = [
        chunk for chunk in retrieved_chunks if chunk.chunk.document_id == str(document_id)
    ]

    assert document_chunks
    assert any("customs clearance" in chunk.chunk.content for chunk in document_chunks)
