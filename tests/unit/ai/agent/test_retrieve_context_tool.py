from uuid import uuid4

import pytest

from app.ai.application.agent.context import AgentContext
from app.ai.application.agent.retrieve_context_tool import (
    RetrieveContextTool,
)
from app.ai.application.services.retrieve_context import (
    RetrieveContextService,
)
from app.ai.domain.rag_models import DocumentChunk, RetrievedChunk
from tests.unit.ai.fakes import (
    FakeEmbeddingProvider,
    FakeVectorStore,
)


@pytest.mark.asyncio
async def test_retrieve_context_tool_uses_agent_tenant_context() -> None:
    tenant_id = uuid4()

    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()

    retrieved_chunk = RetrievedChunk(
        chunk=DocumentChunk(
            id="chunk-1",
            document_id="document-1",
            content="Shipment insurance covers eligible cargo loss.",
            chunk_index=0,
        ),
        score=0.91,
    )

    vector_store.search_results = (retrieved_chunk,)

    retrieve_context_service = RetrieveContextService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    tool = RetrieveContextTool(
        retrieve_context_service=retrieve_context_service,
    )

    result = await tool.execute(
        context=AgentContext(
            tenant_id=tenant_id,
        ),
        query="What does shipment insurance cover?",
    )

    assert result == (retrieved_chunk,)

    assert vector_store.searches == [
        (
            tenant_id,
            (0.1, 0.2, 0.3),
            5,
        )
    ]
