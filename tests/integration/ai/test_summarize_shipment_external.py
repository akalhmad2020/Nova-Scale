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
from app.ai.infrastructure.dependencies import build_llm_provider
from app.core.config import get_settings
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
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment

SetTenantContext = Callable[[UUID], Awaitable[None]]


async def create_shipment_with_timeline(
    *,
    session: AsyncSession,
    tenant_id: UUID,
) -> Shipment:
    customer = Customer(
        tenant_id=tenant_id,
        name="External Summary Customer",
        code=f"EXT-SUMMARY-CUSTOMER-{uuid4()}",
        status=CustomerStatus.ACTIVE,
    )

    origin = Location(
        tenant_id=tenant_id,
        name="External Summary Origin",
        code=f"EXT-SUMMARY-ORIGIN-{uuid4()}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="External Summary Origin Address",
        status=LocationStatus.ACTIVE,
    )

    destination = Location(
        tenant_id=tenant_id,
        name="External Summary Destination",
        code=f"EXT-SUMMARY-DEST-{uuid4()}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Nablus",
        address_line1="External Summary Destination Address",
        status=LocationStatus.ACTIVE,
    )

    hub = Location(
        tenant_id=tenant_id,
        name="External Summary Hub",
        code=f"EXT-SUMMARY-HUB-{uuid4()}",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Jericho",
        address_line1="External Summary Hub Address",
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
        tracking_number=f"EXT-SUMMARY-{uuid4()}",
        reference="EXT-SUMMARY-REF",
        status=ShipmentStatus.IN_TRANSIT,
        service_type=ServiceType.EXPRESS,
        description="Shipment used for external AI summary testing",
        weight=Decimal("18.250"),
        weight_unit=WeightUnit.KG,
        notes="High priority shipment",
    )

    session.add(shipment)
    await session.flush()

    base_time = datetime.now(UTC)

    session.add_all(
        [
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
        ]
    )

    await session.flush()

    return shipment


@pytest.mark.integration
@pytest.mark.external_ai
@pytest.mark.asyncio
async def test_real_llm_summarizes_real_shipment_context(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    tenant = Tenant(
        name="External Shipment Summary Tenant",
        slug=f"external-shipment-summary-{uuid4()}",
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

    settings = get_settings()

    llm_provider = build_llm_provider(
        settings,
    )

    shipment_summary_tool = ShipmentSummaryTool(
        get_shipment=get_get_shipment_use_case(),
        list_shipment_events=get_list_shipment_events_use_case(),
    )

    service = SummarizeShipmentService(
        shipment_summary_tool=shipment_summary_tool,
        generate_text_service=GenerateTextService(
            provider=llm_provider,
        ),
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

    assert response.content.strip()

    normalized_answer = response.content.lower()

    expected_status = ShipmentStatus.IN_TRANSIT.value.lower()
    expected_status_natural = expected_status.replace("_", " ")

    assert expected_status in normalized_answer or expected_status_natural in normalized_answer

    assert shipment.tracking_number.lower() in normalized_answer

    assert expected_status in normalized_answer or expected_status_natural in normalized_answer

    timeline_signals = (
        "created",
        "picked up",
        "picked_up",
        "pick-up",
        "arrived",
        "regional hub",
    )

    matched_timeline_signals = sum(signal in normalized_answer for signal in timeline_signals)

    assert matched_timeline_signals >= 2

    assert "delivered" not in normalized_answer
    assert "cancelled" not in normalized_answer

    timeline_signals = (
        "created",
        "picked up",
        "picked_up",
        "pick-up",
        "arrived",
        "regional hub",
    )

    matched_timeline_signals = sum(signal in normalized_answer for signal in timeline_signals)

    assert matched_timeline_signals >= 2

    assert "delivered" not in normalized_answer
    assert "cancelled" not in normalized_answer
