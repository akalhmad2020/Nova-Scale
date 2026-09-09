from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.agent.shipment_summary_tool import ShipmentSummaryTool
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.application.services.summarize_shipment import (
    SummarizeShipmentService,
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
from tests.unit.ai.fakes import FakeLLMProvider

SetTenantContext = Callable[[UUID], Awaitable[None]]


async def create_shipment_context(
    *,
    session: AsyncSession,
    tenant_id: UUID,
) -> tuple[Shipment, Location]:
    customer = Customer(
        tenant_id=tenant_id,
        name="AI Shipment Summary Customer",
        code=f"AI-SUMMARY-CUSTOMER-{uuid4()}",
        status=CustomerStatus.ACTIVE,
    )

    origin = Location(
        tenant_id=tenant_id,
        name="AI Summary Origin",
        code=f"AI-SUMMARY-ORIGIN-{uuid4()}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="AI Summary Origin Address",
        status=LocationStatus.ACTIVE,
    )

    destination = Location(
        tenant_id=tenant_id,
        name="AI Summary Destination",
        code=f"AI-SUMMARY-DEST-{uuid4()}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Nablus",
        address_line1="AI Summary Destination Address",
        status=LocationStatus.ACTIVE,
    )

    event_location = Location(
        tenant_id=tenant_id,
        name="AI Summary Hub",
        code=f"AI-SUMMARY-HUB-{uuid4()}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Jericho",
        address_line1="AI Summary Hub Address",
        status=LocationStatus.ACTIVE,
    )

    session.add_all(
        [
            customer,
            origin,
            destination,
            event_location,
        ]
    )

    await session.flush()

    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number=f"AI-SUMMARY-{uuid4()}",
        reference="ORDER-AI-100",
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="Electronics shipment for AI summary",
        weight=Decimal("12.500"),
        weight_unit=WeightUnit.KG,
        notes="Handle with care",
    )

    session.add(shipment)

    await session.flush()

    return shipment, event_location


async def create_timeline(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    shipment_id: UUID,
    location_id: UUID,
) -> None:
    base_time = datetime.now(UTC)

    events = [
        ShipmentEvent(
            tenant_id=tenant_id,
            shipment_id=shipment_id,
            event_type=ShipmentEventType.ARRIVED_AT_LOCATION,
            status=ShipmentStatus.IN_TRANSIT,
            location_id=location_id,
            description="Shipment arrived at sorting hub",
            occurred_at=base_time + timedelta(hours=2),
            metadata_={
                "sequence": 3,
            },
        ),
        ShipmentEvent(
            tenant_id=tenant_id,
            shipment_id=shipment_id,
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
            shipment_id=shipment_id,
            event_type=ShipmentEventType.PICKED_UP,
            status=ShipmentStatus.IN_TRANSIT,
            location_id=location_id,
            description="Shipment picked up from origin",
            occurred_at=base_time + timedelta(hours=1),
            metadata_={
                "sequence": 2,
            },
        ),
    ]

    session.add_all(events)

    await session.flush()


def build_summary_service(
    *,
    llm_provider: FakeLLMProvider,
) -> SummarizeShipmentService:
    shipment_summary_tool = ShipmentSummaryTool(
        get_shipment=get_get_shipment_use_case(),
        list_shipment_events=get_list_shipment_events_use_case(),
    )

    return SummarizeShipmentService(
        shipment_summary_tool=shipment_summary_tool,
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_summarize_shipment_uses_real_shipment_timeline(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    tenant = Tenant(
        name="AI Shipment Summary Tenant",
        slug=f"ai-shipment-summary-{uuid4()}",
        status=TenantStatus.ACTIVE,
    )

    db_session.add(tenant)
    await db_session.flush()

    await set_tenant_context(
        tenant.id,
    )

    shipment, event_location = await create_shipment_context(
        session=db_session,
        tenant_id=tenant.id,
    )

    await create_timeline(
        session=db_session,
        tenant_id=tenant.id,
        shipment_id=shipment.id,
        location_id=event_location.id,
    )

    await db_session.commit()

    llm_provider = FakeLLMProvider()

    service = build_summary_service(
        llm_provider=llm_provider,
    )

    tenant_context_token = set_current_tenant_id(
        tenant.id,
    )

    try:
        response = await service.execute(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert response.content == "fake response"
    assert response.model == "fake-model"

    assert len(llm_provider.requests) == 1

    request = llm_provider.requests[0]

    assert request.temperature == 0.0
    assert request.max_tokens == 96
    assert request.context_window == 2048
    assert len(request.messages) == 2

    assert request.messages[0].role == "system"
    assert request.messages[1].role == "user"

    prompt = request.messages[1].content

    assert str(shipment.id) in prompt
    assert shipment.tracking_number in prompt

    assert "reference=ORDER-AI-100" in prompt
    assert "status=in_transit" in prompt
    assert "service=express" in prompt
    assert "description=Electronics shipment for AI summary" in prompt
    assert "weight=12.500 kg" in prompt
    assert "notes=Handle with care" in prompt

    assert "event_count=3" in prompt

    assert "type=created" in prompt
    assert "Shipment created" in prompt

    assert "type=picked_up" in prompt
    assert "Shipment picked up from origin" in prompt

    assert "type=arrived_at_location" in prompt
    assert "Shipment arrived at sorting hub" in prompt

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

    shipment_section = prompt.split(
        "\n\nTimeline:",
        maxsplit=1,
    )[0]

    latest_event_line = next(
        line for line in shipment_section.splitlines() if line.startswith("latest_event=")
    )

    assert "type=arrived_at_location" in latest_event_line
    assert "status=in_transit" in latest_event_line
    assert "Shipment arrived at sorting hub" in latest_event_line


@pytest.mark.integration
@pytest.mark.asyncio
async def test_summarize_shipment_rejects_cross_tenant_access(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    owner_tenant = Tenant(
        name="AI Shipment Summary Owner",
        slug=f"ai-summary-owner-{uuid4()}",
        status=TenantStatus.ACTIVE,
    )

    foreign_tenant = Tenant(
        name="AI Shipment Summary Foreign",
        slug=f"ai-summary-foreign-{uuid4()}",
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

    shipment, event_location = await create_shipment_context(
        session=db_session,
        tenant_id=owner_tenant.id,
    )

    await create_timeline(
        session=db_session,
        tenant_id=owner_tenant.id,
        shipment_id=shipment.id,
        location_id=event_location.id,
    )

    await db_session.commit()

    await set_tenant_context(
        foreign_tenant.id,
    )

    llm_provider = FakeLLMProvider()

    service = build_summary_service(
        llm_provider=llm_provider,
    )

    tenant_context_token = set_current_tenant_id(
        foreign_tenant.id,
    )

    try:
        with pytest.raises(ShipmentNotFoundError):
            await service.execute(
                tenant_id=foreign_tenant.id,
                shipment_id=shipment.id,
            )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert llm_provider.requests == []
