from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.agent.authorization import (
    AgentAuthorizationService,
)
from app.ai.application.agent.decision import AgentDecision
from app.ai.application.agent.get_shipment_tool import GetShipmentTool
from app.ai.application.agent.retrieve_context_tool import RetrieveContextTool
from app.ai.application.agent.shipment_summary_tool import ShipmentSummaryTool
from app.ai.application.dependencies import build_resolve_shipment_service
from app.ai.application.services.analyze_shipment import (
    AnalyzeShipmentService,
)
from app.ai.application.services.analyze_shipment_operations import (
    AnalyzeShipmentOperationsService,
)
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.application.services.retrieve_context import RetrieveContextService
from app.ai.application.services.summarize_shipment import (
    SummarizeShipmentService,
)
from app.ai.infrastructure.agent.langgraph_runtime import (
    LangGraphAgentRuntime,
)
from app.core.tenant_context import (
    reset_current_tenant_id,
    set_current_tenant_id,
)
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.identity.domain.enums import TenantStatus
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location
from app.modules.shipment_events.api.dependencies import (
    get_list_shipment_events_use_case,
)
from app.modules.shipment_events.domain.enums import ShipmentEventType
from app.modules.shipment_events.infrastructure.models.shipment_event import (
    ShipmentEvent,
)
from app.modules.shipments.api.dependencies import (
    get_get_shipment_use_case,
)
from app.modules.shipments.application.exceptions import ShipmentNotFoundError
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

TEST_ROLE_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


async def allow_all_permissions(
    role_id: UUID,
    permission_code: str,
) -> bool:
    del role_id
    del permission_code

    return True


SetTenantContext = Callable[[UUID], Awaitable[None]]


async def create_shipment_with_timeline(
    *,
    session: AsyncSession,
    tenant_id: UUID,
) -> Shipment:
    customer = Customer(
        tenant_id=tenant_id,
        name="Agent Summary Customer",
        code=f"AGENT-SUMMARY-CUSTOMER-{uuid4()}",
        status=CustomerStatus.ACTIVE,
    )

    origin = Location(
        tenant_id=tenant_id,
        name="Agent Summary Origin",
        code=f"AGENT-SUMMARY-ORIGIN-{uuid4()}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Agent Summary Origin Address",
        status=LocationStatus.ACTIVE,
    )

    destination = Location(
        tenant_id=tenant_id,
        name="Agent Summary Destination",
        code=f"AGENT-SUMMARY-DEST-{uuid4()}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Nablus",
        address_line1="Agent Summary Destination Address",
        status=LocationStatus.ACTIVE,
    )

    hub = Location(
        tenant_id=tenant_id,
        name="Agent Summary Hub",
        code=f"AGENT-SUMMARY-HUB-{uuid4()}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Jericho",
        address_line1="Agent Summary Hub Address",
        status=LocationStatus.ACTIVE,
    )

    session.add_all(
        [
            customer,
            origin,
            destination,
            hub,
        ]
    )

    await session.flush()

    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=f"AGENT-SUMMARY-{uuid4()}",
        reference="AGENT-SUMMARY-REF",
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="Shipment used for agent intelligence integration",
        weight=Decimal("15.750"),
        weight_unit=WeightUnit.KG,
        notes="Priority shipment",
    )

    session.add(shipment)
    await session.flush()

    base_time = datetime.now(UTC)

    session.add_all(
        [
            ShipmentEvent(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                event_type=ShipmentEventType.ARRIVED_AT_LOCATION,
                status=ShipmentStatus.IN_TRANSIT,
                location_id=hub.id,
                description="Shipment arrived at regional hub",
                occurred_at=base_time + timedelta(hours=2),
                metadata_={
                    "sequence": 3,
                },
            ),
            ShipmentEvent(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                event_type=ShipmentEventType.CREATED,
                status=None,
                location_id=None,
                description="Shipment created",
                occurred_at=base_time,
                metadata_={
                    "sequence": 1,
                },
            ),
            ShipmentEvent(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                event_type=ShipmentEventType.PICKED_UP,
                status=ShipmentStatus.IN_TRANSIT,
                location_id=origin.id,
                description="Shipment picked up from origin",
                occurred_at=base_time + timedelta(hours=1),
                metadata_={
                    "sequence": 2,
                },
            ),
        ]
    )

    await session.flush()

    return shipment


def build_runtime(
    *,
    planner: FakeAgentPlanner,
    llm_provider: FakeLLMProvider,
) -> LangGraphAgentRuntime:
    shipment_summary_tool = ShipmentSummaryTool(
        get_shipment=get_get_shipment_use_case(),
        list_shipment_events=get_list_shipment_events_use_case(),
    )
    analyze_shipment_service = AnalyzeShipmentService(
        shipment_summary_tool=shipment_summary_tool,
        analyze_operations_service=AnalyzeShipmentOperationsService(),
    )

    summarize_shipment_service = SummarizeShipmentService(
        shipment_summary_tool=shipment_summary_tool,
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )

    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()

    retrieve_context_service = RetrieveContextService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    return LangGraphAgentRuntime(
        agent_planner=planner,
        authorization_service=AgentAuthorizationService(
            permission_checker=allow_all_permissions,
        ),
        resolve_shipment_service=build_resolve_shipment_service(),
        get_shipment_tool=GetShipmentTool(
            get_shipment=get_get_shipment_use_case(),
        ),
        summarize_shipment_service=summarize_shipment_service,
        retrieve_context_tool=RetrieveContextTool(
            retrieve_context_service=retrieve_context_service,
        ),
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
        analyze_shipment_service=analyze_shipment_service,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_summarizes_real_shipment_timeline(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    tenant = Tenant(
        name="Agent Shipment Summary Tenant",
        slug=f"agent-shipment-summary-{uuid4()}",
        status=TenantStatus.ACTIVE,
    )

    db_session.add(tenant)
    await db_session.flush()

    await set_tenant_context(
        tenant.id,
    )

    shipment = await create_shipment_with_timeline(
        session=db_session,
        tenant_id=tenant.id,
    )

    await db_session.commit()

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="summarize_shipment",
        shipment_identifier=shipment.tracking_number,
    )

    llm_provider = FakeLLMProvider()

    runtime = build_runtime(
        planner=planner,
        llm_provider=llm_provider,
    )

    question = (
        f"Summarize shipment {shipment.tracking_number} and give me its operational timeline."
    )

    tenant_context_token = set_current_tenant_id(
        tenant.id,
    )

    try:
        answer = await runtime.execute(
            tenant_id=tenant.id,
            role_id=TEST_ROLE_ID,
            question=question,
        )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert answer == "fake response"

    assert planner.questions == [
        question,
    ]

    assert len(llm_provider.requests) == 1

    request = llm_provider.requests[0]

    assert request.temperature == 0.0
    assert request.max_tokens == 96
    assert request.context_window == 2048

    prompt = request.messages[-1].content

    assert str(shipment.id) in prompt
    assert shipment.tracking_number in prompt
    assert "reference=AGENT-SUMMARY-REF" in prompt
    assert "status=in_transit" in prompt
    assert "service=express" in prompt
    assert "description=Shipment used for agent intelligence integration" in prompt
    assert "weight=15.750 kg" in prompt
    assert "notes=Priority shipment" in prompt
    assert "event_count=3" in prompt

    assert "type=created" in prompt
    assert "type=picked_up" in prompt
    assert "type=arrived_at_location" in prompt

    timeline_section = prompt.split(
        "\n\nTimeline:",
        maxsplit=1,
    )[1]

    created_position = timeline_section.index(
        "type=created",
    )

    picked_up_position = timeline_section.index(
        "type=picked_up",
    )

    arrived_position = timeline_section.index(
        "type=arrived_at_location",
    )

    assert created_position < picked_up_position < arrived_position


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_shipment_summary_resolves_reference(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    tenant = Tenant(
        name="Agent Reference Summary Tenant",
        slug=f"agent-reference-summary-{uuid4()}",
        status=TenantStatus.ACTIVE,
    )

    db_session.add(tenant)
    await db_session.flush()

    await set_tenant_context(
        tenant.id,
    )

    shipment = await create_shipment_with_timeline(
        session=db_session,
        tenant_id=tenant.id,
    )

    await db_session.commit()

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="summarize_shipment",
        shipment_identifier="AGENT-SUMMARY-REF",
    )

    llm_provider = FakeLLMProvider()

    runtime = build_runtime(
        planner=planner,
        llm_provider=llm_provider,
    )

    question = "Summarize shipment AGENT-SUMMARY-REF and give me its timeline."

    tenant_context_token = set_current_tenant_id(
        tenant.id,
    )

    try:
        answer = await runtime.execute(
            tenant_id=tenant.id,
            role_id=TEST_ROLE_ID,
            question=question,
        )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert answer == "fake response"

    assert len(llm_provider.requests) == 1

    prompt = llm_provider.requests[0].messages[-1].content

    assert str(shipment.id) in prompt
    assert shipment.tracking_number in prompt
    assert "reference=AGENT-SUMMARY-REF" in prompt


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_shipment_summary_respects_tenant_isolation(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    owner_tenant = Tenant(
        name="Agent Shipment Summary Owner",
        slug=f"agent-summary-owner-{uuid4()}",
        status=TenantStatus.ACTIVE,
    )

    foreign_tenant = Tenant(
        name="Agent Shipment Summary Foreign",
        slug=f"agent-summary-foreign-{uuid4()}",
        status=TenantStatus.ACTIVE,
    )

    db_session.add_all(
        [
            owner_tenant,
            foreign_tenant,
        ]
    )

    await db_session.flush()

    await set_tenant_context(
        owner_tenant.id,
    )

    shipment = await create_shipment_with_timeline(
        session=db_session,
        tenant_id=owner_tenant.id,
    )

    await db_session.commit()

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="summarize_shipment",
        shipment_identifier=shipment.tracking_number,
    )

    llm_provider = FakeLLMProvider()

    runtime = build_runtime(
        planner=planner,
        llm_provider=llm_provider,
    )

    question = f"Summarize shipment {shipment.tracking_number} and give me its timeline."

    tenant_context_token = set_current_tenant_id(
        foreign_tenant.id,
    )

    try:
        with pytest.raises(ShipmentNotFoundError):
            await runtime.execute(
                tenant_id=foreign_tenant.id,
                role_id=TEST_ROLE_ID,
                question=question,
            )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert llm_provider.requests == []
