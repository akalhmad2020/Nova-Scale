from datetime import timedelta
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.ai.application.agent.action_models import AgentActionProposal
from app.ai.application.agent.authorization import (
    AgentAuthorizationService,
)
from app.ai.application.agent.conversation import AgentContinuation
from app.ai.application.agent.conversation_context import (
    ConversationContext,
    ConversationMessage,
)
from app.ai.application.agent.decision import AgentDecision
from app.ai.application.agent.exceptions import AgentPlanningError
from app.ai.application.agent.get_shipment_tool import GetShipmentTool
from app.ai.application.agent.retrieve_context_tool import (
    RetrieveContextTool,
)
from app.ai.application.agent.shipment_operational_models import (
    ShipmentOperationalAnalysis,
    ShipmentOperationalIssue,
)
from app.ai.application.ports.agent_planner import AgentPlanner
from app.ai.application.services.analyze_shipment import (
    AnalyzeShipmentService,
)
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.application.services.prepare_shipment_action import (
    PrepareShipmentActionService,
)
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
from app.modules.identity.domain.permissions import Permissions
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

TEST_ROLE_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


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


async def allow_all_permissions(
    role_id: UUID,
    permission_code: str,
) -> bool:
    del role_id
    del permission_code

    return True


def make_prepare_shipment_action_service() -> PrepareShipmentActionService:
    service_mock = MagicMock(
        spec=PrepareShipmentActionService,
    )

    return cast(
        PrepareShipmentActionService,
        service_mock,
    )


def make_runtime(
    *,
    planner: AgentPlanner,
    uow: FakeUnitOfWork,
    llm_provider: FakeLLMProvider,
    summarize_shipment_service: SummarizeShipmentService,
    analyze_shipment_service: AnalyzeShipmentService | None = None,
    prepare_shipment_action_service: PrepareShipmentActionService | None = None,
    retrieve_context_tool: RetrieveContextTool | None = None,
) -> LangGraphAgentRuntime:
    if retrieve_context_tool is None:
        retrieve_context_tool = make_retrieve_context_tool()

    if analyze_shipment_service is None:
        analyze_shipment_service, _ = make_analyze_shipment_service()

    if prepare_shipment_action_service is None:
        prepare_shipment_action_service = make_prepare_shipment_action_service()

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
        prepare_shipment_action_service=prepare_shipment_action_service,
        retrieve_context_tool=retrieve_context_tool,
        authorization_service=AgentAuthorizationService(
            permission_checker=allow_all_permissions,
        ),
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
        role_id=TEST_ROLE_ID,
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
        role_id=TEST_ROLE_ID,
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
        role_id=TEST_ROLE_ID,
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
        role_id=TEST_ROLE_ID,
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

    result = await runtime.execute(
        tenant_id=uuid4(),
        role_id=TEST_ROLE_ID,
        question="Where is shipment SHIP-001?",
    )

    assert (
        result == "I couldn't find a shipment matching 'SHIP-001' "
        "in the active workspace. Please check the tracking number, "
        "shipment UUID, or reference and try again."
    )

    assert len(llm_provider.requests) == 0


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
        role_id=TEST_ROLE_ID,
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
        role_id=TEST_ROLE_ID,
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
        role_id=TEST_ROLE_ID,
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
            role_id=TEST_ROLE_ID,
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
        role_id=TEST_ROLE_ID,
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
        role_id=TEST_ROLE_ID,
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


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_handles_ambiguous_shipment_reference() -> None:
    tenant_id = uuid4()

    first_shipment = make_shipment(
        tenant_id=tenant_id,
    )
    first_shipment.tracking_number = "SHIP-001"

    second_shipment = make_shipment(
        tenant_id=tenant_id,
    )
    second_shipment.tracking_number = "SHIP-002"

    uow = FakeUnitOfWork()
    uow.shipments.add(first_shipment)
    uow.shipments.add(second_shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipment",
        shipment_identifier="ORDER-100",
    )

    llm_provider = FakeLLMProvider()

    summarize_shipment_service, summarize_execute_mock = make_summarize_shipment_service()
    analyze_shipment_service, analyze_execute_mock = make_analyze_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
        analyze_shipment_service=analyze_shipment_service,
    )

    result = await runtime.execute(
        tenant_id=tenant_id,
        role_id=TEST_ROLE_ID,
        question="Where is shipment ORDER-100?",
    )

    assert result == (
        "I found multiple shipments matching 'ORDER-100'. "
        "Please provide the shipment tracking number or UUID "
        "so I can identify the correct shipment."
    )

    assert llm_provider.requests == []
    summarize_execute_mock.assert_not_awaited()
    analyze_execute_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_continues_after_ambiguous_shipment_selection() -> None:
    tenant_id = uuid4()

    first_shipment = make_shipment(
        tenant_id=tenant_id,
    )
    first_shipment.tracking_number = "SHIP-001"

    second_shipment = make_shipment(
        tenant_id=tenant_id,
    )
    second_shipment.tracking_number = "SHIP-002"

    uow = FakeUnitOfWork()
    uow.shipments.add(first_shipment)
    uow.shipments.add(second_shipment)

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

    first_result = await runtime.execute_with_context(
        tenant_id=tenant_id,
        role_id=TEST_ROLE_ID,
        question="Where is shipment ORDER-100?",
    )

    assert first_result.answer == (
        "I found multiple shipments matching 'ORDER-100'. "
        "Please provide the shipment tracking number or UUID "
        "so I can identify the correct shipment."
    )

    assert first_result.continuation == AgentContinuation(
        kind="shipment_selection",
        route="get_shipment",
        original_identifier="ORDER-100",
    )

    assert planner.questions == [
        "Where is shipment ORDER-100?",
    ]

    second_result = await runtime.execute_with_context(
        tenant_id=tenant_id,
        role_id=TEST_ROLE_ID,
        question="SHIP-002",
        continuation=first_result.continuation,
    )

    assert second_result.answer == "fake response"
    assert second_result.continuation is None

    # The continuation must resume the original route directly.
    # The planner must not classify the follow-up again.
    assert planner.questions == [
        "Where is shipment ORDER-100?",
    ]

    assert len(llm_provider.requests) == 1

    prompt = llm_provider.requests[0].messages[-1].content

    assert f"Shipment id: {second_shipment.id}" in prompt
    assert "Tracking number: SHIP-002" in prompt
    assert "Reference: ORDER-100" in prompt
    assert f"Shipment id: {first_shipment.id}" not in prompt


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_denies_unauthorized_tool() -> None:
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
    analyze_shipment_service, _ = make_analyze_shipment_service()

    async def deny_permissions(
        role_id: UUID,
        permission_code: str,
    ) -> bool:
        del role_id
        del permission_code

        return False

    runtime = LangGraphAgentRuntime(
        agent_planner=planner,
        authorization_service=AgentAuthorizationService(
            permission_checker=deny_permissions,
        ),
        resolve_shipment_service=ResolveShipmentService(
            unit_of_work=uow,
        ),
        get_shipment_tool=GetShipmentTool(
            get_shipment=GetShipment(uow),
        ),
        summarize_shipment_service=summarize_shipment_service,
        analyze_shipment_service=analyze_shipment_service,
        prepare_shipment_action_service=make_prepare_shipment_action_service(),
        retrieve_context_tool=make_retrieve_context_tool(),
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )

    result = await runtime.execute(
        tenant_id=tenant_id,
        role_id=TEST_ROLE_ID,
        question="Where is shipment SHIP-001?",
    )

    assert result == ("You do not have permission to use the requested NovaScale capability.")

    assert llm_provider.requests == []


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_reauthorizes_continuation() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    shipment.tracking_number = "SHIP-002"

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    planner = FakeAgentPlanner()

    llm_provider = FakeLLMProvider()

    summarize_shipment_service, summarize_execute_mock = make_summarize_shipment_service()

    analyze_shipment_service, analyze_execute_mock = make_analyze_shipment_service()

    permission_checks: list[
        tuple[
            UUID,
            str,
        ]
    ] = []

    async def deny_permissions(
        role_id: UUID,
        permission_code: str,
    ) -> bool:
        permission_checks.append(
            (
                role_id,
                permission_code,
            )
        )

        return False

    runtime = LangGraphAgentRuntime(
        agent_planner=planner,
        authorization_service=AgentAuthorizationService(
            permission_checker=deny_permissions,
        ),
        resolve_shipment_service=ResolveShipmentService(
            unit_of_work=uow,
        ),
        get_shipment_tool=GetShipmentTool(
            get_shipment=GetShipment(uow),
        ),
        summarize_shipment_service=summarize_shipment_service,
        analyze_shipment_service=analyze_shipment_service,
        prepare_shipment_action_service=make_prepare_shipment_action_service(),
        retrieve_context_tool=make_retrieve_context_tool(),
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )

    continuation = AgentContinuation(
        kind="shipment_selection",
        route="get_shipment",
        original_identifier="ORDER-100",
    )

    result = await runtime.execute_with_context(
        tenant_id=tenant_id,
        role_id=TEST_ROLE_ID,
        question="SHIP-002",
        continuation=continuation,
    )

    assert result.answer == (
        "You do not have permission to use the requested NovaScale capability."
    )

    assert result.continuation is None

    assert permission_checks == [
        (
            TEST_ROLE_ID,
            Permissions.SHIPMENT_READ,
        )
    ]

    # A continuation must bypass only planning,
    # never authorization.
    assert planner.questions == []

    # No shipment capability or downstream LLM call
    # may run after authorization is denied.
    assert llm_provider.requests == []

    summarize_execute_mock.assert_not_awaited()
    analyze_execute_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_gets_multiple_shipments() -> None:
    tenant_id = uuid4()

    first_shipment = make_shipment(
        tenant_id=tenant_id,
    )
    first_shipment.tracking_number = "SHIP-001"
    first_shipment.reference = "ORDER-100"

    second_shipment = make_shipment(
        tenant_id=tenant_id,
    )
    second_shipment.tracking_number = "SHIP-002"
    second_shipment.reference = "ORDER-200"

    uow = FakeUnitOfWork()
    uow.shipments.add(first_shipment)
    uow.shipments.add(second_shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipments",
        shipment_identifiers=(
            "SHIP-001",
            "SHIP-002",
        ),
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
        role_id=TEST_ROLE_ID,
        question="Compare SHIP-001 and SHIP-002.",
    )

    assert result == "fake response"

    assert planner.questions == [
        "Compare SHIP-001 and SHIP-002.",
    ]

    assert len(llm_provider.requests) == 1

    request = llm_provider.requests[0]

    assert request.temperature == 0.0

    prompt = request.messages[-1].content

    assert "Compare SHIP-001 and SHIP-002." in prompt

    assert "Shipment 1:" in prompt
    assert f"Shipment id: {first_shipment.id}" in prompt
    assert "Tracking number: SHIP-001" in prompt
    assert "Reference: ORDER-100" in prompt

    assert "Shipment 2:" in prompt
    assert f"Shipment id: {second_shipment.id}" in prompt
    assert "Tracking number: SHIP-002" in prompt
    assert "Reference: ORDER-200" in prompt

    first_position = prompt.index("Tracking number: SHIP-001")
    second_position = prompt.index("Tracking number: SHIP-002")

    assert first_position < second_position


@pytest.mark.asyncio
async def test_multi_shipment_returns_partial_result_when_one_is_missing() -> None:
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )
    shipment.tracking_number = "SHIP-001"
    shipment.reference = "ORDER-100"

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipments",
        shipment_identifiers=(
            "SHIP-001",
            "SHIP-MISSING",
        ),
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
        role_id=TEST_ROLE_ID,
        question="Compare SHIP-001 and SHIP-MISSING.",
    )

    assert result == "fake response"

    assert planner.questions == [
        "Compare SHIP-001 and SHIP-MISSING.",
    ]

    assert len(llm_provider.requests) == 1

    prompt = llm_provider.requests[0].messages[-1].content

    assert "Shipment 1:" in prompt
    assert "Identifier: SHIP-001" in prompt
    assert "Resolution status: resolved" in prompt
    assert f"Shipment id: {shipment.id}" in prompt
    assert "Tracking number: SHIP-001" in prompt

    assert "Shipment 2:" in prompt
    assert "Identifier: SHIP-MISSING" in prompt
    assert "Resolution status: not_found" in prompt
    assert "The shipment could not be found for the current tenant." in prompt


@pytest.mark.asyncio
async def test_multi_shipment_returns_partial_result_for_ambiguous_identifier() -> None:
    tenant_id = uuid4()

    first_match = make_shipment(
        tenant_id=tenant_id,
    )
    first_match.tracking_number = "SHIP-001"
    first_match.reference = "ORDER-100"

    second_match = make_shipment(
        tenant_id=tenant_id,
    )
    second_match.tracking_number = "SHIP-002"
    second_match.reference = "ORDER-100"

    unique_shipment = make_shipment(
        tenant_id=tenant_id,
    )
    unique_shipment.tracking_number = "SHIP-003"
    unique_shipment.reference = "ORDER-300"

    uow = FakeUnitOfWork()
    uow.shipments.add(first_match)
    uow.shipments.add(second_match)
    uow.shipments.add(unique_shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipments",
        shipment_identifiers=(
            "ORDER-100",
            "SHIP-003",
        ),
    )

    llm_provider = FakeLLMProvider()

    summarize_shipment_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
    )

    result = await runtime.execute_with_context(
        tenant_id=tenant_id,
        role_id=TEST_ROLE_ID,
        question="Compare ORDER-100 and SHIP-003.",
    )

    assert result.answer == "fake response"
    assert result.continuation is None

    assert planner.questions == [
        "Compare ORDER-100 and SHIP-003.",
    ]

    assert len(llm_provider.requests) == 1

    prompt = llm_provider.requests[0].messages[-1].content

    assert "Shipment 1:" in prompt
    assert "Identifier: ORDER-100" in prompt
    assert "Resolution status: ambiguous" in prompt
    assert "The identifier matches multiple shipments." in prompt
    assert "A tracking number or shipment UUID is required to identify the shipment." in prompt

    assert "Shipment 2:" in prompt
    assert "Identifier: SHIP-003" in prompt
    assert "Resolution status: resolved" in prompt
    assert f"Shipment id: {unique_shipment.id}" in prompt
    assert "Tracking number: SHIP-003" in prompt


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_multi_shipment_handles_all_missing() -> None:
    tenant_id = uuid4()

    uow = FakeUnitOfWork()

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipments",
        shipment_identifiers=(
            "SHIP-MISSING-001",
            "SHIP-MISSING-002",
        ),
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
        role_id=TEST_ROLE_ID,
        question=("Compare SHIP-MISSING-001 and SHIP-MISSING-002."),
    )

    assert result == "fake response"

    assert len(llm_provider.requests) == 1

    prompt = llm_provider.requests[0].messages[-1].content

    assert "Identifier: SHIP-MISSING-001" in prompt
    assert "Identifier: SHIP-MISSING-002" in prompt

    assert prompt.count("Resolution status: not_found") == 2

    assert "Shipment id:" not in prompt


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_passes_conversation_context_to_planner() -> None:
    tenant_id = uuid4()

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

    conversation_context = ConversationContext(
        messages=(
            ConversationMessage(
                role="user",
                content="Compare SHIP-001 and SHIP-002.",
            ),
            ConversationMessage(
                role="assistant",
                content="SHIP-001 appears more delayed.",
            ),
        )
    )

    await runtime.execute(
        tenant_id=tenant_id,
        role_id=TEST_ROLE_ID,
        question="Which one is more delayed?",
        conversation_context=conversation_context,
    )

    assert planner.questions == [
        "Which one is more delayed?",
    ]

    assert planner.conversation_contexts == [
        conversation_context,
    ]


@pytest.mark.asyncio
async def test_runtime_handles_contextual_multi_shipment_follow_up() -> None:
    tenant_id = uuid4()

    first_shipment = make_shipment(
        tenant_id=tenant_id,
    )
    first_shipment.tracking_number = "SHIP-001"

    second_shipment = make_shipment(
        tenant_id=tenant_id,
    )
    second_shipment.tracking_number = "SHIP-002"

    uow = FakeUnitOfWork()
    uow.shipments.add(first_shipment)
    uow.shipments.add(second_shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="get_shipments",
        shipment_identifiers=(
            "SHIP-001",
            "SHIP-002",
        ),
    )

    llm_provider = FakeLLMProvider()

    summarize_shipment_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
    )

    conversation_context = ConversationContext(
        messages=(
            ConversationMessage(
                role="user",
                content="Compare SHIP-001 and SHIP-002.",
            ),
            ConversationMessage(
                role="assistant",
                content="SHIP-001 appears more delayed.",
            ),
        )
    )

    answer = await runtime.execute(
        tenant_id=tenant_id,
        role_id=TEST_ROLE_ID,
        question="Which one is more delayed?",
        conversation_context=conversation_context,
    )

    assert answer == "fake response"

    assert planner.questions == [
        "Which one is more delayed?",
    ]

    assert planner.conversation_contexts == [
        conversation_context,
    ]

    assert len(llm_provider.requests) == 1

    prompt = llm_provider.requests[0].messages[-1].content

    assert "SHIP-001" in prompt
    assert "SHIP-002" in prompt
    assert str(first_shipment.id) in prompt
    assert str(second_shipment.id) in prompt


class FailingAgentPlanner:
    def __init__(self) -> None:
        self.calls = 0

    async def plan(
        self,
        *,
        question: str,
        conversation_context: ConversationContext | None = None,
    ) -> AgentDecision:
        del question
        del conversation_context

        self.calls += 1

        raise AgentPlanningError("planner failed")


@pytest.mark.asyncio
async def test_runtime_falls_back_to_direct_answer_when_planner_fails() -> None:
    tenant_id = uuid4()

    planner = FailingAgentPlanner()

    llm_provider = FakeLLMProvider()

    uow = FakeUnitOfWork()

    summarize_shipment_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
    )

    answer = await runtime.execute(
        tenant_id=tenant_id,
        role_id=TEST_ROLE_ID,
        question="What is a tracking number?",
    )

    assert answer == "fake response"

    assert planner.calls == 2

    assert len(llm_provider.requests) == 1

    request = llm_provider.requests[0]

    prompt = request.messages[-1].content

    assert prompt == "What is a tracking number?"


class RetryAgentPlanner:
    def __init__(
        self,
        *,
        decision: AgentDecision,
    ) -> None:
        self.decision = decision
        self.calls = 0

    async def plan(
        self,
        *,
        question: str,
        conversation_context: ConversationContext | None = None,
    ) -> AgentDecision:
        del question
        del conversation_context

        self.calls += 1

        if self.calls == 1:
            raise AgentPlanningError("first planner attempt failed")

        return self.decision


@pytest.mark.asyncio
async def test_runtime_retries_planner_once_after_planning_error() -> None:
    tenant_id = uuid4()

    planner = RetryAgentPlanner(
        decision=AgentDecision(
            route="direct_answer",
        ),
    )

    llm_provider = FakeLLMProvider()

    uow = FakeUnitOfWork()

    summarize_shipment_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
    )

    answer = await runtime.execute(
        tenant_id=tenant_id,
        role_id=TEST_ROLE_ID,
        question="What is a tracking number?",
    )

    assert answer == "fake response"

    assert planner.calls == 2

    assert len(llm_provider.requests) == 1


@pytest.mark.asyncio
async def test_runtime_logs_planner_retry_without_prompt_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tenant_id = uuid4()

    planner = RetryAgentPlanner(
        decision=AgentDecision(
            route="direct_answer",
        ),
    )

    llm_provider = FakeLLMProvider()
    uow = FakeUnitOfWork()

    summarize_shipment_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
    )

    sensitive_question = "Sensitive shipment question"

    with caplog.at_level(
        "WARNING",
        logger="novascale.ai",
    ):
        await runtime.execute(
            tenant_id=tenant_id,
            role_id=TEST_ROLE_ID,
            question=sensitive_question,
        )

    record = next(
        record
        for record in caplog.records
        if (
            record.name == "novascale.ai"
            and record.getMessage() == "AI agent planner attempt failed"
        )
    )

    record_fields = vars(record)

    assert record_fields["ai_operation"] == "agent_planning"
    assert record_fields["ai_outcome"] == "retry"
    assert record_fields["attempt"] == 1

    assert sensitive_question not in record.getMessage()


@pytest.mark.asyncio
async def test_runtime_logs_planner_fallback_without_prompt_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tenant_id = uuid4()

    planner = FailingAgentPlanner()

    llm_provider = FakeLLMProvider()
    uow = FakeUnitOfWork()

    summarize_shipment_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=llm_provider,
        summarize_shipment_service=summarize_shipment_service,
    )

    sensitive_question = "Sensitive shipment question"

    with caplog.at_level(
        "WARNING",
        logger="novascale.ai",
    ):
        await runtime.execute(
            tenant_id=tenant_id,
            role_id=TEST_ROLE_ID,
            question=sensitive_question,
        )

    record = next(
        record
        for record in caplog.records
        if (
            record.name == "novascale.ai"
            and record.getMessage() == "AI agent planner fallback activated"
        )
    )

    record_fields = vars(record)

    assert record_fields["ai_operation"] == "agent_planning"
    assert record_fields["ai_outcome"] == "fallback"
    assert record_fields["attempts"] == 2

    assert sensitive_question not in record.getMessage()


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_prepares_status_transition_action() -> None:
    tenant_id = uuid4()
    shipment = make_shipment(tenant_id=tenant_id)

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    statuses = list(ShipmentStatus)
    target_status = next(status for status in statuses if status != ShipmentStatus(shipment.status))

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="transition_shipment_status",
        shipment_identifier=shipment.tracking_number,
        target_shipment_status=target_status,
    )

    proposal = AgentActionProposal(
        action_type="transition_shipment_status",
        shipment_id=shipment.id,
        shipment_identifier=shipment.tracking_number,
        expected_status=ShipmentStatus(shipment.status),
        target_status=target_status,
        summary="Transition shipment after confirmation.",
    )

    prepare_service_mock = MagicMock(
        spec=PrepareShipmentActionService,
    )
    prepare_service_mock.prepare_transition = AsyncMock(
        return_value=proposal,
    )
    prepare_service = cast(
        PrepareShipmentActionService,
        prepare_service_mock,
    )

    summarize_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=FakeLLMProvider(),
        summarize_shipment_service=summarize_service,
        prepare_shipment_action_service=prepare_service,
    )

    result = await runtime.execute_with_context(
        tenant_id=tenant_id,
        role_id=TEST_ROLE_ID,
        question="Move this shipment to the requested status.",
    )

    assert result.action_proposal == proposal
    assert result.continuation is None
    assert "requires explicit confirmation" in result.answer


@pytest.mark.asyncio
async def test_langgraph_agent_runtime_prepares_notes_update_action() -> None:
    tenant_id = uuid4()
    shipment = make_shipment(tenant_id=tenant_id)

    uow = FakeUnitOfWork()
    uow.shipments.add(shipment)

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="update_shipment_notes",
        shipment_identifier=shipment.tracking_number,
        shipment_notes="Keep upright",
    )

    proposal = AgentActionProposal(
        action_type="update_shipment_notes",
        shipment_id=shipment.id,
        shipment_identifier=shipment.tracking_number,
        expected_status=ShipmentStatus(shipment.status),
        expected_notes=shipment.notes,
        new_notes="Keep upright",
        summary="Update shipment notes after confirmation.",
    )

    prepare_service_mock = MagicMock(
        spec=PrepareShipmentActionService,
    )
    prepare_service_mock.prepare_notes_update = AsyncMock(
        return_value=proposal,
    )
    prepare_service = cast(
        PrepareShipmentActionService,
        prepare_service_mock,
    )

    summarize_service, _ = make_summarize_shipment_service()

    runtime = make_runtime(
        planner=planner,
        uow=uow,
        llm_provider=FakeLLMProvider(),
        summarize_shipment_service=summarize_service,
        prepare_shipment_action_service=prepare_service,
    )

    result = await runtime.execute_with_context(
        tenant_id=tenant_id,
        role_id=TEST_ROLE_ID,
        question="Set the shipment notes to Keep upright.",
    )

    assert result.action_proposal == proposal
    assert result.continuation is None
    assert "requires explicit confirmation" in result.answer
