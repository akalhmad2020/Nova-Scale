from uuid import uuid4

import pytest

from app.ai.application.services.retrieve_context import RetrieveContextService
from app.ai.domain.rag_models import DocumentChunk, RetrievedChunk
from tests.unit.ai.fakes import FakeEmbeddingProvider, FakeVectorStore


@pytest.mark.asyncio
async def test_retrieve_context_embeds_query_and_searches_vector_store() -> None:
    tenant_id = uuid4()

    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()

    vector_store.search_results = (
        RetrievedChunk(
            chunk=DocumentChunk(
                id="document-1:0",
                document_id="document-1",
                content="Shipment tracking information",
                chunk_index=0,
            ),
            score=0.95,
        ),
    )

    service = RetrieveContextService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    results = await service.execute(
        tenant_id=tenant_id,
        query="Where is my shipment?",
        limit=3,
    )

    assert results == vector_store.search_results

    assert vector_store.searches == [
        (
            tenant_id,
            (0.1, 0.2, 0.3),
            3,
        )
    ]


@pytest.mark.asyncio
async def test_retrieve_context_filters_results_below_minimum_score() -> None:
    tenant_id = uuid4()

    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()

    relevant_chunk = RetrievedChunk(
        chunk=DocumentChunk(
            id="document-1:0",
            document_id="document-1",
            content="Shipment NOVA-100 is in transit.",
            chunk_index=0,
        ),
        score=0.82,
    )

    irrelevant_chunk = RetrievedChunk(
        chunk=DocumentChunk(
            id="document-2:0",
            document_id="document-2",
            content="Billing invoice information.",
            chunk_index=0,
        ),
        score=0.21,
    )

    vector_store.search_results = (
        relevant_chunk,
        irrelevant_chunk,
    )

    service = RetrieveContextService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        minimum_score=0.5,
    )

    results = await service.execute(
        tenant_id=tenant_id,
        query="What is the status of shipment NOVA-100?",
    )

    assert results == (relevant_chunk,)


@pytest.mark.asyncio
async def test_retrieve_context_returns_empty_when_all_results_are_below_threshold() -> None:
    tenant_id = uuid4()

    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()

    vector_store.search_results = (
        RetrievedChunk(
            chunk=DocumentChunk(
                id="document-1:0",
                document_id="document-1",
                content="Unrelated information.",
                chunk_index=0,
            ),
            score=0.31,
        ),
        RetrievedChunk(
            chunk=DocumentChunk(
                id="document-2:0",
                document_id="document-2",
                content="More unrelated information.",
                chunk_index=0,
            ),
            score=0.12,
        ),
    )

    service = RetrieveContextService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        minimum_score=0.5,
    )

    results = await service.execute(
        tenant_id=tenant_id,
        query="Where is shipment NOVA-100?",
    )

    assert results == ()


@pytest.mark.asyncio
async def test_retrieve_context_returns_empty_for_blank_query() -> None:
    tenant_id = uuid4()

    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()

    service = RetrieveContextService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    results = await service.execute(
        tenant_id=tenant_id,
        query="   ",
    )

    assert results == ()
    assert vector_store.searches == []
