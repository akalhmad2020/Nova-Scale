from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.agent.decision import AgentDecision
from app.ai.application.agent.get_shipment_tool import GetShipmentTool
from app.ai.application.agent.retrieve_context_tool import RetrieveContextTool
from app.ai.application.agent.shipment_summary_tool import ShipmentSummaryTool
from app.ai.application.dependencies import build_resolve_shipment_service
from app.ai.application.services.analyze_shipment import AnalyzeShipmentService
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

SetTenantContext = Callable[[UUID], Awaitable[None]]


async def create_operational_shipment(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    latest_event_age: timedelta,
) -> Shipment:
    customer = Customer(
        tenant_id=tenant_id,
        name="Agent Operations Customer",
        code=f"AGENT-OPS-CUSTOMER-{uuid4()}",
        status=CustomerStatus.ACTIVE,
    )

    origin = Location(
        tenant_id=tenant_id,
        name="Agent Operations Origin",
        code=f"AGENT-OPS-ORIGIN-{uuid4()}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Agent Operations Origin Address",
        status=LocationStatus.ACTIVE,
    )

    destination = Location(
        tenant_id=tenant_id,
        name="Agent Operations Destination",
        code=f"AGENT-OPS-DEST-{uuid4()}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Nablus",
        address_line1="Agent Operations Destination Address",
        status=LocationStatus.ACTIVE,
    )

    session.add_all(
        [
            customer,
            origin,
            destination,
        ]
    )

    await session.flush()

    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=f"AGENT-OPS-{uuid4()}",
        reference=f"AGENT-OPS-REF-{uuid4()}",
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="Shipment used for operational issue analysis",
        weight=Decimal("20.000"),
        weight_unit=WeightUnit.KG,
        notes="Monitor operational activity",
    )

    session.add(shipment)
    await session.flush()

    latest_event_time = datetime.now(UTC) - latest_event_age

    session.add(
        ShipmentEvent(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
            event_type=ShipmentEventType.PICKED_UP,
            status=ShipmentStatus.IN_TRANSIT,
            location_id=origin.id,
            description="Shipment picked up from origin",
            occurred_at=latest_event_time,
            metadata_={
                "source": "integration-test",
            },
        )
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

    summarize_shipment_service = SummarizeShipmentService(
        shipment_summary_tool=shipment_summary_tool,
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )

    analyze_shipment_service = AnalyzeShipmentService(
        shipment_summary_tool=shipment_summary_tool,
        analyze_operations_service=AnalyzeShipmentOperationsService(
            stale_in_transit_after=timedelta(hours=24),
        ),
    )

    retrieve_context_service = RetrieveContextService(
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=FakeVectorStore(),
    )

    return LangGraphAgentRuntime(
        agent_planner=planner,
        resolve_shipment_service=build_resolve_shipment_service(),
        get_shipment_tool=GetShipmentTool(
            get_shipment=get_get_shipment_use_case(),
        ),
        summarize_shipment_service=summarize_shipment_service,
        analyze_shipment_service=analyze_shipment_service,
        retrieve_context_tool=RetrieveContextTool(
            retrieve_context_service=retrieve_context_service,
        ),
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_detects_stale_in_transit_shipment(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    tenant = Tenant(
        name="Agent Operations Stale Tenant",
        slug=f"agent-operations-stale-{uuid4()}",
        status=TenantStatus.ACTIVE,
    )

    db_session.add(tenant)
    await db_session.flush()

    await set_tenant_context(
        tenant.id,
    )

    shipment = await create_operational_shipment(
        session=db_session,
        tenant_id=tenant.id,
        latest_event_age=timedelta(hours=30),
    )

    await db_session.commit()

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="analyze_shipment_operations",
        shipment_identifier=shipment.tracking_number,
    )

    llm_provider = FakeLLMProvider()

    runtime = build_runtime(
        planner=planner,
        llm_provider=llm_provider,
    )

    question = f"Is there anything wrong with shipment {shipment.tracking_number}?"

    tenant_context_token = set_current_tenant_id(
        tenant.id,
    )

    try:
        answer = await runtime.execute(
            tenant_id=tenant.id,
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

    prompt = llm_provider.requests[0].messages[-1].content

    assert "stale_in_transit" in prompt
    assert "severity=warning" in prompt
    assert "Highest severity: warning" in prompt
    assert "Risk score: 25/100" in prompt
    assert "Risk level: medium" in prompt
    assert "Issue count: 1" in prompt
    assert "age=30h" in prompt
    assert (
        "recommended_action=Verify the shipment's current location and contact the carrier"
    ) in prompt
    assert "Shipment is in transit but has not received a recent operational event." in prompt


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_reports_healthy_recent_in_transit_shipment(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    tenant = Tenant(
        name="Agent Operations Healthy Tenant",
        slug=f"agent-operations-healthy-{uuid4()}",
        status=TenantStatus.ACTIVE,
    )

    db_session.add(tenant)
    await db_session.flush()

    await set_tenant_context(
        tenant.id,
    )

    shipment = await create_operational_shipment(
        session=db_session,
        tenant_id=tenant.id,
        latest_event_age=timedelta(hours=2),
    )

    await db_session.commit()

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="analyze_shipment_operations",
        shipment_identifier=shipment.reference,
    )

    llm_provider = FakeLLMProvider()

    runtime = build_runtime(
        planner=planner,
        llm_provider=llm_provider,
    )

    question = f"Does shipment {shipment.reference} have any operational issues?"

    tenant_context_token = set_current_tenant_id(
        tenant.id,
    )

    try:
        answer = await runtime.execute(
            tenant_id=tenant.id,
            question=question,
        )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert answer == "fake response"

    assert len(llm_provider.requests) == 1

    prompt = llm_provider.requests[0].messages[-1].content

    assert "No operational issues were detected for this shipment." in prompt
    assert "Highest severity: info" in prompt
    assert "Risk score: 0/100" in prompt
    assert "Risk level: low" in prompt


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_operational_analysis_respects_tenant_isolation(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    owner_tenant = Tenant(
        name="Agent Operations Owner",
        slug=f"agent-operations-owner-{uuid4()}",
        status=TenantStatus.ACTIVE,
    )

    foreign_tenant = Tenant(
        name="Agent Operations Foreign",
        slug=f"agent-operations-foreign-{uuid4()}",
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

    shipment = await create_operational_shipment(
        session=db_session,
        tenant_id=owner_tenant.id,
        latest_event_age=timedelta(hours=30),
    )

    await db_session.commit()

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="analyze_shipment_operations",
        shipment_identifier=shipment.tracking_number,
    )

    llm_provider = FakeLLMProvider()

    runtime = build_runtime(
        planner=planner,
        llm_provider=llm_provider,
    )

    tenant_context_token = set_current_tenant_id(
        foreign_tenant.id,
    )

    try:
        with pytest.raises(ShipmentNotFoundError):
            await runtime.execute(
                tenant_id=foreign_tenant.id,
                question=(f"Analyze shipment {shipment.tracking_number} for operational issues."),
            )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert llm_provider.requests == []
