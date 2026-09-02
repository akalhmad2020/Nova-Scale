from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.ai.application.agent.decision import AgentDecision
from app.ai.application.agent.get_shipment_tool import GetShipmentTool
from app.ai.application.agent.retrieve_context_tool import (
    RetrieveContextTool,
)
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.application.services.retrieve_context import RetrieveContextService
from app.ai.domain.rag_models import DocumentChunk, RetrievedChunk
from app.ai.infrastructure.agent.langgraph_runtime import (
    LangGraphAgentRuntime,
)
from app.modules.shipments.application.exceptions import ShipmentNotFoundError
from app.modules.shipments.application.use_cases.get_shipment import GetShipment
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment
from tests.unit.ai.fakes import (
    FakeAgentPlanner,
    FakeEmbeddingProvider,
    FakeLLMProvider,
    FakeVectorStore,
)
from tests.unit.shipments.fakes import FakeUnitOfWork


def make_shipment(
    *,
    tenant_id: UUID,
) -> Shipment:
    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        tracking_number="SHIP-001",
        reference="ORDER-100",
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.STANDARD,
        description="Electronics shipment",
        weight=Decimal("12.500"),
        weight_unit=WeightUnit.KG,
        notes="Handle with care",
    )
    shipment.id = uuid4()

    return shipment


def make_retrieve_context_tool(
    *,
    vector_store: FakeVectorStore | None = None,
) -> RetrieveContextTool:
    embedding_provider = FakeEmbeddingProvider()

    if vector_store is None:
        vector_store = FakeVectorStore()

    retrieve_context_service = RetrieveContextService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    return RetrieveContextTool(
        retrieve_context_service=retrieve_context_service,
    )


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_direct_answer_route() -> None:
    planner = FakeAgentPlanner()
    llm_provider = FakeLLMProvider()
    uow = FakeUnitOfWork()

    runtime = LangGraphAgentRuntime(
        agent_planner=planner,
        get_shipment_tool=GetShipmentTool(
            get_shipment=GetShipment(uow),
        ),
        retrieve_context_tool=make_retrieve_context_tool(),
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )

    tenant_id = uuid4()

    result = await runtime.execute(
        tenant_id=tenant_id,
        question="What can you help me with?",
    )

    assert result == "fake response"

    assert planner.questions == [
        "What can you help me with?",
    ]

    assert len(llm_provider.requests) == 1

    request = llm_provider.requests[0]

    assert request.temperature == 0.0

    assert request.messages[1].role == "user"
    assert request.messages[1].content == ("What can you help me with?")


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_get_shipment_route() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipment",
        shipment_id=shipment.id,
    )

    llm_provider = FakeLLMProvider()

    runtime = LangGraphAgentRuntime(
        agent_planner=planner,
        get_shipment_tool=GetShipmentTool(
            get_shipment=GetShipment(uow),
        ),
        retrieve_context_tool=make_retrieve_context_tool(),
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )

    result = await runtime.execute(
        tenant_id=tenant_id,
        question="Where is shipment SHIP-001?",
    )

    assert result == "fake response"

    assert planner.questions == [
        "Where is shipment SHIP-001?",
    ]

    assert len(llm_provider.requests) == 1

    request = llm_provider.requests[0]

    assert request.temperature == 0.0

    prompt = request.messages[1].content

    assert "Where is shipment SHIP-001?" in prompt
    assert f"Shipment id: {shipment.id}" in prompt
    assert "Tracking number: SHIP-001" in prompt
    assert "Reference: ORDER-100" in prompt
    assert "Status: in_transit" in prompt
    assert "Service type: standard" in prompt
    assert "Description: Electronics shipment" in prompt
    assert "Weight: 12.500 kg" in prompt
    assert "Notes: Handle with care" in prompt


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_uses_runtime_tenant_context() -> None:
    shipment = make_shipment(
        tenant_id=uuid4(),
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipment",
        shipment_id=shipment.id,
    )

    llm_provider = FakeLLMProvider()

    runtime = LangGraphAgentRuntime(
        agent_planner=planner,
        get_shipment_tool=GetShipmentTool(
            get_shipment=GetShipment(uow),
        ),
        retrieve_context_tool=make_retrieve_context_tool(),
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )

    with pytest.raises(ShipmentNotFoundError):
        await runtime.execute(
            tenant_id=uuid4(),
            question="Where is this shipment?",
        )


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_retrieve_context_route() -> None:
    tenant_id = uuid4()

    vector_store = FakeVectorStore()

    retrieved_chunk = RetrievedChunk(
        chunk=DocumentChunk(
            id="chunk-1",
            document_id="document-1",
            content=("Shipment insurance covers eligible cargo loss during transportation."),
            chunk_index=0,
        ),
        score=0.91,
    )

    vector_store.search_results = (retrieved_chunk,)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="retrieve_context",
    )

    llm_provider = FakeLLMProvider()
    uow = FakeUnitOfWork()

    runtime = LangGraphAgentRuntime(
        agent_planner=planner,
        get_shipment_tool=GetShipmentTool(
            get_shipment=GetShipment(uow),
        ),
        retrieve_context_tool=make_retrieve_context_tool(
            vector_store=vector_store,
        ),
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )

    result = await runtime.execute(
        tenant_id=tenant_id,
        question="What does our shipment insurance cover?",
    )

    assert result == "fake response"

    assert planner.questions == [
        "What does our shipment insurance cover?",
    ]

    assert vector_store.searches == [
        (
            tenant_id,
            (0.1, 0.2, 0.3),
            5,
        )
    ]

    assert len(llm_provider.requests) == 1

    request = llm_provider.requests[0]

    assert request.temperature == 0.0

    prompt = request.messages[1].content

    assert "What does our shipment insurance cover?" in prompt
    assert "Document: document-1" in prompt
    assert "Chunk: 0" in prompt
    assert ("Shipment insurance covers eligible cargo loss during transportation.") in prompt
