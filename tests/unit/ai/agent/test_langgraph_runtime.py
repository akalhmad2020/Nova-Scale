from datetime import timedelta
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.ai.application.agent.decision import AgentDecision
from app.ai.application.agent.get_shipment_tool import GetShipmentTool
from app.ai.application.agent.retrieve_context_tool import (
    RetrieveContextTool,
)
from app.ai.application.agent.shipment_operational_models import (
    ShipmentOperationalAnalysis,
    ShipmentOperationalIssue,
)
from app.ai.application.services.analyze_shipment import (
    AnalyzeShipmentService,
)
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.application.services.resolve_shipment import ResolveShipmentService
from app.ai.application.services.retrieve_context import RetrieveContextService
from app.ai.application.services.summarize_shipment import (
    SummarizeShipmentService,
)
from app.ai.domain.models import LLMResponse
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


def make_analyze_shipment_service(
    *,
    analysis: ShipmentOperationalAnalysis | None = None,
) -> tuple[
    AnalyzeShipmentService,
    AsyncMock,
]:
    if analysis is None:
        analysis = ShipmentOperationalAnalysis(
            issues=(),
        )

    execute_mock = AsyncMock(
        return_value=analysis,
    )

    service_mock = MagicMock(
        spec=AnalyzeShipmentService,
    )

    service_mock.execute = execute_mock

    return (
        cast(
            AnalyzeShipmentService,
            service_mock,
        ),
        execute_mock,
    )


def make_summarize_shipment_service() -> tuple[
    SummarizeShipmentService,
    AsyncMock,
]:
    execute_mock = AsyncMock(
        return_value=LLMResponse(
            content="fake shipment summary",
            model="fake-model",
        )
    )

    service_mock = MagicMock(
        spec=SummarizeShipmentService,
    )

    service_mock.execute = execute_mock

    return (
        cast(
            SummarizeShipmentService,
            service_mock,
        ),
        execute_mock,
    )


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


def make_runtime(
    *,
    planner: FakeAgentPlanner,
    uow: FakeUnitOfWork,
    llm_provider: FakeLLMProvider,
    summarize_shipment_service: SummarizeShipmentService,
    analyze_shipment_service: AnalyzeShipmentService | None = None,
    retrieve_context_tool: RetrieveContextTool | None = None,
) -> LangGraphAgentRuntime:
    if retrieve_context_tool is None:
        retrieve_context_tool = make_retrieve_context_tool()

    if analyze_shipment_service is None:
        analyze_shipment_service, _ = make_analyze_shipment_service()

    return LangGraphAgentRuntime(
        agent_planner=planner,
        resolve_shipment_service=ResolveShipmentService(
            unit_of_work=uow,
        ),
        get_shipment_tool=GetShipmentTool(
            get_shipment=GetShipment(uow),
        ),
        summarize_shipment_service=summarize_shipment_service,
        analyze_shipment_service=analyze_shipment_service,
        retrieve_context_tool=retrieve_context_tool,
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_direct_answer_route() -> None:
    planner = FakeAgentPlanner()
    llm_provider = FakeLLMProvider()
    uow = FakeUnitOfWork()

    summarize_shipment_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
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
    assert request.messages[1].content == "What can you help me with?"


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_get_shipment_by_tracking_number() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipment",
        shipment_identifier="SHIP-001",
    )

    llm_provider = FakeLLMProvider()

    summarize_shipment_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
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
async def test_langgraph_agent_runtime_get_shipment_by_reference() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipment",
        shipment_identifier="ORDER-100",
    )

    llm_provider = FakeLLMProvider()

    summarize_shipment_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
    )

    result = await runtime.execute(
        tenant_id=tenant_id,
        question="Where is shipment ORDER-100?",
    )

    assert result == "fake response"

    prompt = llm_provider.requests[0].messages[-1].content

    assert f"Shipment id: {shipment.id}" in prompt
    assert "Tracking number: SHIP-001" in prompt


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_get_shipment_by_uuid() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipment",
        shipment_identifier=str(shipment.id),
    )

    llm_provider = FakeLLMProvider()

    summarize_shipment_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
    )

    result = await runtime.execute(
        tenant_id=tenant_id,
        question=f"Where is shipment {shipment.id}?",
    )

    assert result == "fake response"

    prompt = llm_provider.requests[0].messages[-1].content

    assert f"Shipment id: {shipment.id}" in prompt


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
        shipment_identifier="SHIP-001",
    )

    llm_provider = FakeLLMProvider()

    summarize_shipment_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
    )

    with pytest.raises(ShipmentNotFoundError):
        await runtime.execute(
            tenant_id=uuid4(),
            question="Where is shipment SHIP-001?",
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

    summarize_shipment_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
        retrieve_context_tool=make_retrieve_context_tool(
            vector_store=vector_store,
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

    prompt = llm_provider.requests[0].messages[-1].content

    assert "What does our shipment insurance cover?" in prompt
    assert "Document: document-1" in prompt
    assert "Chunk: 0" in prompt
    assert ("Shipment insurance covers eligible cargo loss during transportation.") in prompt


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_summarize_shipment_by_tracking_number() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="summarize_shipment",
        shipment_identifier="SHIP-001",
    )

    summarize_shipment_service, execute_mock = make_summarize_shipment_service()

    llm_provider = FakeLLMProvider()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
    )

    result = await runtime.execute(
        tenant_id=tenant_id,
        question="Summarize shipment SHIP-001.",
    )

    assert result == "fake shipment summary"

    assert planner.questions == [
        "Summarize shipment SHIP-001.",
    ]

    execute_mock.assert_awaited_once_with(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
    )

    assert llm_provider.requests == []


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_summarize_shipment_by_reference() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="summarize_shipment",
        shipment_identifier="ORDER-100",
    )

    summarize_shipment_service, execute_mock = make_summarize_shipment_service()

    llm_provider = FakeLLMProvider()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
    )

    result = await runtime.execute(
        tenant_id=tenant_id,
        question="Summarize shipment ORDER-100.",
    )

    assert result == "fake shipment summary"

    execute_mock.assert_awaited_once_with(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
    )


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_requires_shipment_identifier() -> None:
    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="summarize_shipment",
        shipment_identifier=None,
    )

    summarize_shipment_service, execute_mock = make_summarize_shipment_service()

    llm_provider = FakeLLMProvider()
    uow = FakeUnitOfWork()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
    )

    with pytest.raises(
        RuntimeError,
        match="Shipment identifier is required for shipment route",
    ):
        await runtime.execute(
            tenant_id=uuid4(),
            question="Summarize my shipment.",
        )

    execute_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_analyzes_shipment_operations() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="analyze_shipment_operations",
        shipment_identifier="SHIP-001",
    )

    analysis = ShipmentOperationalAnalysis(
        issues=(
            ShipmentOperationalIssue(
                code="stale_in_transit",
                severity="warning",
                message=("Shipment is in transit but has not received a recent operational event."),
                recommended_action=(
                    "Verify the shipment's current location and contact "
                    "the carrier if no recent tracking update is available."
                ),
                age=timedelta(hours=30),
            ),
        ),
    )

    analyze_shipment_service, execute_mock = make_analyze_shipment_service(
        analysis=analysis,
    )

    summarize_shipment_service, _ = make_summarize_shipment_service()

    llm_provider = FakeLLMProvider()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
        analyze_shipment_service=analyze_shipment_service,
    )

    result = await runtime.execute(
        tenant_id=tenant_id,
        question=("Is there anything wrong with shipment SHIP-001?"),
    )

    assert result == "fake response"

    execute_mock.assert_awaited_once_with(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
    )

    assert len(llm_provider.requests) == 1

    request = llm_provider.requests[0]

    assert request.temperature == 0.0

    prompt = request.messages[-1].content

    assert "Is there anything wrong with shipment SHIP-001?" in prompt

    assert "stale_in_transit" in prompt
    assert "severity=warning" in prompt
    assert "Highest severity: warning" in prompt
    assert "Risk score: 25/100" in prompt
    assert "Risk level: medium" in prompt
    assert "Issue count: 1" in prompt
    assert "age=30h 0m" in prompt

    assert (
        "recommended_action=Verify the shipment's current location "
        "and contact the carrier" in prompt
    )


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_reports_clean_operational_analysis() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="analyze_shipment_operations",
        shipment_identifier="ORDER-100",
    )

    analysis = ShipmentOperationalAnalysis(
        issues=(),
    )

    analyze_shipment_service, execute_mock = make_analyze_shipment_service(
        analysis=analysis,
    )

    summarize_shipment_service, _ = make_summarize_shipment_service()

    llm_provider = FakeLLMProvider()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
        analyze_shipment_service=analyze_shipment_service,
    )

    result = await runtime.execute(
        tenant_id=tenant_id,
        question=("Does shipment ORDER-100 have any operational issues?"),
    )

    assert result == "fake response"

    execute_mock.assert_awaited_once_with(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
    )

    assert len(llm_provider.requests) == 1

    prompt = llm_provider.requests[0].messages[-1].content

    assert "Does shipment ORDER-100 have any operational issues?" in prompt

    assert "No operational issues were detected for this shipment." in prompt

    assert "Highest severity: info" in prompt
    assert "Risk score: 0/100" in prompt
    assert "Risk level: low" in prompt
