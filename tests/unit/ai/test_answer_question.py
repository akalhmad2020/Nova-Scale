from uuid import uuid4

import pytest

from app.ai.application.services.answer_question import AnswerQuestionService
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.application.services.retrieve_context import RetrieveContextService
from app.ai.domain.rag_models import DocumentChunk, RetrievedChunk
from tests.unit.ai.fakes import (
    FakeEmbeddingProvider,
    FakeLLMProvider,
    FakeVectorStore,
)


@pytest.mark.asyncio
async def test_answer_question_uses_retrieved_context() -> None:
    tenant_id = uuid4()

    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()
    llm_provider = FakeLLMProvider()

    source = RetrievedChunk(
        chunk=DocumentChunk(
            id="document-1:0",
            document_id="document-1",
            content="Shipment NOVA-100 is currently in transit.",
            chunk_index=0,
        ),
        score=0.95,
    )

    vector_store.search_results = (source,)

    retrieve_context_service = RetrieveContextService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    generate_text_service = GenerateTextService(
        provider=llm_provider,
    )

    service = AnswerQuestionService(
        retrieve_context_service=retrieve_context_service,
        generate_text_service=generate_text_service,
    )

    answer = await service.execute(
        tenant_id=tenant_id,
        question="What is the status of shipment NOVA-100?",
    )

    assert answer.content == "fake response"
    assert answer.model == "fake-model"
    assert answer.sources == (source,)

    assert len(llm_provider.requests) == 1

    request = llm_provider.requests[0]

    assert request.temperature == 0.0

    prompt = request.messages[-1].content

    assert "Shipment NOVA-100 is currently in transit." in prompt
    assert "What is the status of shipment NOVA-100?" in prompt
    assert "document-1" in prompt


@pytest.mark.asyncio
async def test_answer_question_does_not_call_llm_without_relevant_context() -> None:
    tenant_id = uuid4()

    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()
    llm_provider = FakeLLMProvider()

    retrieve_context_service = RetrieveContextService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    generate_text_service = GenerateTextService(
        provider=llm_provider,
    )

    service = AnswerQuestionService(
        retrieve_context_service=retrieve_context_service,
        generate_text_service=generate_text_service,
    )

    answer = await service.execute(
        tenant_id=tenant_id,
        question="Where is shipment UNKNOWN?",
    )

    assert answer.content == ("I do not have enough relevant information to answer this question.")
    assert answer.model == "none"
    assert answer.sources == ()

    assert llm_provider.requests == []
