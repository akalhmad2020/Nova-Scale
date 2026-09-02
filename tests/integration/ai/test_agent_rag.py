from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.dependencies import build_agent_runtime
from app.ai.application.services.chunk_text import ChunkTextService
from app.ai.application.services.embed_document import EmbedDocumentService
from app.ai.application.services.ingest_document import IngestDocumentService
from app.ai.infrastructure.dependencies import build_embedding_provider
from app.ai.infrastructure.vector_store.postgres_vector_store import (
    PostgresVectorStore,
)
from app.core.config import get_settings


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_answers_from_real_rag_context(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid4()
    document_id = str(uuid4())

    settings = get_settings()

    embedding_provider = build_embedding_provider(settings)

    vector_store = PostgresVectorStore(
        session=db_session,
    )

    embed_document_service = EmbedDocumentService(
        chunk_text_service=ChunkTextService(
            chunk_size=1000,
            chunk_overlap=150,
        ),
        embedding_provider=embedding_provider,
    )

    ingest_document_service = IngestDocumentService(
        embed_document_service=embed_document_service,
        vector_store=vector_store,
    )

    indexed_chunks = await ingest_document_service.execute(
        tenant_id=tenant_id,
        document_id=document_id,
        text=(
            "NovaScale tenant shipping policy states that damaged cargo "
            "must be reported within 48 hours of delivery. "
            "The report must include the shipment reference and "
            "supporting evidence."
        ),
    )

    assert indexed_chunks > 0

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    answer = await runtime.execute(
        tenant_id=tenant_id,
        question=(
            "According to our tenant shipping documents, "
            "within how many hours must damaged cargo be reported?"
        ),
    )

    assert answer.strip()

    normalized_answer = answer.lower()

    assert "48" in normalized_answer

@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_rag_cannot_retrieve_context_from_another_tenant(
    db_session: AsyncSession,
) -> None:
    owner_tenant_id = uuid4()
    foreign_tenant_id = uuid4()
    document_id = str(uuid4())

    settings = get_settings()

    embedding_provider = build_embedding_provider(settings)

    vector_store = PostgresVectorStore(
        session=db_session,
    )

    embed_document_service = EmbedDocumentService(
        chunk_text_service=ChunkTextService(
            chunk_size=1000,
            chunk_overlap=150,
        ),
        embedding_provider=embedding_provider,
    )

    ingest_document_service = IngestDocumentService(
        embed_document_service=embed_document_service,
        vector_store=vector_store,
    )

    indexed_chunks = await ingest_document_service.execute(
        tenant_id=owner_tenant_id,
        document_id=document_id,
        text=(
            "NovaScale confidential tenant policy states that "
            "damaged cargo must be reported within 72 hours."
        ),
    )

    assert indexed_chunks > 0

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    answer = await runtime.execute(
        tenant_id=foreign_tenant_id,
        question=(
            "According to our tenant documents, "
            "within how many hours must damaged cargo be reported?"
        ),
    )

    assert answer.strip()

    normalized_answer = answer.lower()

    assert "72" not in normalized_answer