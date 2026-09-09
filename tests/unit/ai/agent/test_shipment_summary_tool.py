from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.ai.application.agent.shipment_summary_tool import (
    ShipmentSummaryTool,
)
from app.modules.shipment_events.application.use_cases.list_shipment_events import (
    ListShipmentEvents,
    ListShipmentEventsQuery,
)
from app.modules.shipment_events.domain.enums import ShipmentEventType
from app.modules.shipment_events.infrastructure.models.shipment_event import (
    ShipmentEvent,
)
from app.modules.shipments.application.use_cases.get_shipment import (
    GetShipment,
    GetShipmentQuery,
)
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment


def build_shipment(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
) -> Shipment:
    return cast(
        Shipment,
        SimpleNamespace(
            id=shipment_id,
            tenant_id=tenant_id,
            customer_id=uuid4(),
            origin_location_id=uuid4(),
            destination_location_id=uuid4(),
            tracking_number="NS-TRACK-001",
            reference="CUSTOMER-REF-001",
            status=ShipmentStatus.IN_TRANSIT,
            service_type=ServiceType.EXPRESS,
            description="Electronics shipment",
            weight=Decimal("12.500"),
            weight_unit=WeightUnit.KG,
            notes="Handle carefully",
        ),
    )


def build_event(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
    event_type: ShipmentEventType,
    status: ShipmentStatus | None,
    occurred_at: datetime,
    description: str,
) -> ShipmentEvent:
    return cast(
        ShipmentEvent,
        SimpleNamespace(
            id=uuid4(),
            tenant_id=tenant_id,
            shipment_id=shipment_id,
            event_type=event_type,
            status=status,
            location_id=uuid4(),
            description=description,
            occurred_at=occurred_at,
            metadata_={
                "source": "unit-test",
            },
        ),
    )


@pytest.mark.asyncio
async def test_shipment_summary_tool_builds_grounded_context() -> None:
    tenant_id = uuid4()
    shipment_id = uuid4()

    shipment = build_shipment(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
    )

    older_event = build_event(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
        event_type=ShipmentEventType.PICKED_UP,
        status=ShipmentStatus.IN_TRANSIT,
        occurred_at=datetime(
            2026,
            9,
            1,
            8,
            0,
            tzinfo=UTC,
        ),
        description="Shipment picked up from origin.",
    )

    latest_event = build_event(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
        event_type=ShipmentEventType.DEPARTED_LOCATION,
        status=ShipmentStatus.IN_TRANSIT,
        occurred_at=datetime(
            2026,
            9,
            1,
            12,
            30,
            tzinfo=UTC,
        ),
        description="Shipment departed distribution center.",
    )

    get_shipment = AsyncMock(spec=GetShipment)
    get_shipment.execute.return_value = shipment

    list_shipment_events = AsyncMock(spec=ListShipmentEvents)

    # Deliberately return events out of order.
    list_shipment_events.execute.return_value = [
        latest_event,
        older_event,
    ]

    tool = ShipmentSummaryTool(
        get_shipment=get_shipment,
        list_shipment_events=list_shipment_events,
    )

    result = await tool.execute(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
    )

    assert result.shipment_id == shipment_id
    assert result.tenant_id == tenant_id
    assert result.tracking_number == "NS-TRACK-001"
    assert result.reference == "CUSTOMER-REF-001"
    assert result.status == ShipmentStatus.IN_TRANSIT.value
    assert result.service_type == ServiceType.EXPRESS.value
    assert result.weight == Decimal("12.500")
    assert result.weight_unit == WeightUnit.KG.value

    assert result.event_count == 2

    assert result.events[0].event_type == ShipmentEventType.PICKED_UP.value
    assert result.events[1].event_type == ShipmentEventType.DEPARTED_LOCATION.value

    assert result.latest_event is not None
    assert result.latest_event.event_type == ShipmentEventType.DEPARTED_LOCATION.value
    assert result.latest_event.description == "Shipment departed distribution center."

    get_shipment.execute.assert_awaited_once_with(
        GetShipmentQuery(
            tenant_id=tenant_id,
            shipment_id=shipment_id,
        )
    )

    list_shipment_events.execute.assert_awaited_once_with(
        ListShipmentEventsQuery(
            tenant_id=tenant_id,
            shipment_id=shipment_id,
        )
    )


@pytest.mark.asyncio
async def test_shipment_summary_tool_handles_empty_timeline() -> None:
    tenant_id = uuid4()
    shipment_id = uuid4()

    shipment = build_shipment(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
    )

    get_shipment = AsyncMock(spec=GetShipment)
    get_shipment.execute.return_value = shipment

    list_shipment_events = AsyncMock(spec=ListShipmentEvents)
    list_shipment_events.execute.return_value = []

    tool = ShipmentSummaryTool(
        get_shipment=get_shipment,
        list_shipment_events=list_shipment_events,
    )

    result = await tool.execute(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
    )

    assert result.event_count == 0
    assert result.events == ()
    assert result.latest_event is None
