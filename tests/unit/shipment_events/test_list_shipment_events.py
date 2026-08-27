from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.shipment_events.application.exceptions import (
    ShipmentEventShipmentNotFoundError,
)
from app.modules.shipment_events.application.use_cases.list_shipment_events import (
    ListShipmentEvents,
    ListShipmentEventsQuery,
)
from app.modules.shipment_events.domain.enums import ShipmentEventType
from app.modules.shipment_events.infrastructure.models.shipment_event import (
    ShipmentEvent,
)
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment
from tests.unit.shipment_events.fakes import FakeUnitOfWork


def make_shipment(
    *,
    tenant_id: UUID,
    tracking_number: str,
) -> Shipment:
    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        tracking_number=tracking_number,
        status=ShipmentStatus.DRAFT,
        service_type=ServiceType.STANDARD,
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.KG,
    )
    shipment.id = uuid4()

    return shipment


def make_event(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
    event_type: ShipmentEventType,
    occurred_at: datetime,
) -> ShipmentEvent:
    event = ShipmentEvent(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
        event_type=event_type,
        status=None,
        location_id=None,
        description=None,
        occurred_at=occurred_at,
        metadata_=None,
        created_by_user_id=None,
    )
    event.id = uuid4()
    event.created_at = occurred_at

    return event


async def test_list_shipment_events_returns_timeline_in_order() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
    )

    now = datetime.now(UTC)

    later = make_event(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        event_type=ShipmentEventType.ARRIVED_AT_LOCATION,
        occurred_at=now + timedelta(hours=2),
    )

    first = make_event(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        event_type=ShipmentEventType.CREATED,
        occurred_at=now,
    )

    middle = make_event(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        event_type=ShipmentEventType.PICKED_UP,
        occurred_at=now + timedelta(hours=1),
    )

    uow.shipments.add(shipment)

    uow.shipment_events.add(later)
    uow.shipment_events.add(first)
    uow.shipment_events.add(middle)

    result = await ListShipmentEvents(uow).execute(
        ListShipmentEventsQuery(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
        )
    )

    assert result == [
        first,
        middle,
        later,
    ]


async def test_list_shipment_events_excludes_other_shipments() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
    )

    other_shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-002",
    )

    now = datetime.now(UTC)

    expected = make_event(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        event_type=ShipmentEventType.CREATED,
        occurred_at=now,
    )

    other = make_event(
        tenant_id=tenant_id,
        shipment_id=other_shipment.id,
        event_type=ShipmentEventType.CREATED,
        occurred_at=now,
    )

    uow.shipments.add(shipment)
    uow.shipments.add(other_shipment)

    uow.shipment_events.add(expected)
    uow.shipment_events.add(other)

    result = await ListShipmentEvents(uow).execute(
        ListShipmentEventsQuery(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
        )
    )

    assert result == [expected]


async def test_list_shipment_events_returns_empty_list() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
    )

    uow.shipments.add(shipment)

    result = await ListShipmentEvents(uow).execute(
        ListShipmentEventsQuery(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
        )
    )

    assert result == []


async def test_list_shipment_events_rejects_unknown_shipment() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(ShipmentEventShipmentNotFoundError):
        await ListShipmentEvents(uow).execute(
            ListShipmentEventsQuery(
                tenant_id=uuid4(),
                shipment_id=uuid4(),
            )
        )

    assert uow.rolled_back is True


async def test_list_shipment_events_rejects_shipment_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    shipment = make_shipment(
        tenant_id=uuid4(),
        tracking_number="SHIP-001",
    )

    uow.shipments.add(shipment)

    with pytest.raises(ShipmentEventShipmentNotFoundError):
        await ListShipmentEvents(uow).execute(
            ListShipmentEventsQuery(
                tenant_id=uuid4(),
                shipment_id=shipment.id,
            )
        )

    assert uow.rolled_back is True
