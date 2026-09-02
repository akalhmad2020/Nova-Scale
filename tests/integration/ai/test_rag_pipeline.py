from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.services.answer_question import AnswerQuestionService
from app.ai.application.services.chunk_text import ChunkTextService
from app.ai.application.services.embed_document import EmbedDocumentService
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.application.services.ingest_document import IngestDocumentService
from app.ai.application.services.retrieve_context import RetrieveContextService
from app.ai.infrastructure.dependencies import (
    build_embedding_provider,
    build_llm_provider,
)
from app.ai.infrastructure.vector_store.postgres_vector_store import (
    PostgresVectorStore,
)
from app.core.config import get_settings


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_pipeline_end_to_end(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid4()

    shipment_document_id = str(uuid4())
    billing_document_id = str(uuid4())

    settings = get_settings()

    embedding_provider = build_embedding_provider(settings)
    llm_provider = build_llm_provider(settings)

    vector_store = PostgresVectorStore(
        session=db_session,
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

    retrieve_context_service = RetrieveContextService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    generate_text_service = GenerateTextService(
        provider=llm_provider,
    )

    answer_question_service = AnswerQuestionService(
        retrieve_context_service=retrieve_context_service,
        generate_text_service=generate_text_service,
    )

    shipment_chunks = await ingest_document_service.execute(
        tenant_id=tenant_id,
        document_id=shipment_document_id,
        text=(
            "Shipment NOVA-100 is currently in transit. "
            "The shipment departed the Ramallah distribution center "
            "and is expected to reach the destination tomorrow."
        ),
    )

    billing_chunks = await ingest_document_service.execute(
        tenant_id=tenant_id,
        document_id=billing_document_id,
        text=(
            "Invoice INV-200 has been paid successfully. "
            "The payment was received and the invoice balance is zero."
        ),
    )

    assert shipment_chunks > 0
    assert billing_chunks > 0

    answer = await answer_question_service.execute(
        tenant_id=tenant_id,
        question="What is the status of shipment NOVA-100?",
        limit=2,
    )

    assert answer.content.strip()
    assert answer.model == settings.ai_ollama_model

    assert answer.sources

    assert answer.sources[0].chunk.document_id == shipment_document_id

    retrieved_document_ids = {source.chunk.document_id for source in answer.sources}

    assert shipment_document_id in retrieved_document_ids
