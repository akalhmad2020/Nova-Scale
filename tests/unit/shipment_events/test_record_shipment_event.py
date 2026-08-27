from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location
from app.modules.shipment_events.application.exceptions import (
    ShipmentEventLocationNotFoundError,
    ShipmentEventShipmentNotFoundError,
)
from app.modules.shipment_events.application.use_cases.record_shipment_event import (
    RecordShipmentEvent,
    RecordShipmentEventCommand,
)
from app.modules.shipment_events.domain.enums import ShipmentEventType
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
) -> Shipment:
    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        tracking_number="SHIP-EVENT-001",
        status=ShipmentStatus.DRAFT,
        service_type=ServiceType.STANDARD,
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.KG,
    )
    shipment.id = uuid4()

    return shipment


def make_location(
    *,
    tenant_id: UUID,
) -> Location:
    location = Location(
        tenant_id=tenant_id,
        name="Event Location",
        code="EVENT-LOC-001",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Event Location Address",
        status=LocationStatus.ACTIVE,
    )
    location.id = uuid4()

    return location


async def test_record_shipment_event_creates_event() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    location = make_location(
        tenant_id=tenant_id,
    )

    uow.shipments.add(shipment)
    uow.locations.add(location)

    occurred_at = datetime.now(UTC)
    created_by_user_id = uuid4()

    result = await RecordShipmentEvent(uow).execute(
        RecordShipmentEventCommand(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
            event_type=ShipmentEventType.STATUS_CHANGED,
            occurred_at=occurred_at,
            status=ShipmentStatus.READY,
            location_id=location.id,
            description="  Shipment is ready  ",
            metadata={
                "source": "unit-test",
            },
            created_by_user_id=created_by_user_id,
        )
    )

    assert result.tenant_id == tenant_id
    assert result.shipment_id == shipment.id
    assert result.event_type == ShipmentEventType.STATUS_CHANGED
    assert result.status == ShipmentStatus.READY
    assert result.location_id == location.id
    assert result.description == "Shipment is ready"
    assert result.occurred_at == occurred_at
    assert result.metadata_ == {
        "source": "unit-test",
    }
    assert result.created_by_user_id == created_by_user_id

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_record_shipment_event_allows_event_without_location() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow.shipments.add(shipment)

    result = await RecordShipmentEvent(uow).execute(
        RecordShipmentEventCommand(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
            event_type=ShipmentEventType.NOTE_ADDED,
            occurred_at=datetime.now(UTC),
            description="Operational note",
        )
    )

    assert result.location_id is None
    assert result.status is None
    assert result.event_type == ShipmentEventType.NOTE_ADDED
    assert uow.committed is True


async def test_record_shipment_event_rejects_unknown_shipment() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(ShipmentEventShipmentNotFoundError):
        await RecordShipmentEvent(uow).execute(
            RecordShipmentEventCommand(
                tenant_id=uuid4(),
                shipment_id=uuid4(),
                event_type=ShipmentEventType.NOTE_ADDED,
                occurred_at=datetime.now(UTC),
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_record_shipment_event_rejects_shipment_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    shipment = make_shipment(
        tenant_id=uuid4(),
    )

    uow.shipments.add(shipment)

    with pytest.raises(ShipmentEventShipmentNotFoundError):
        await RecordShipmentEvent(uow).execute(
            RecordShipmentEventCommand(
                tenant_id=uuid4(),
                shipment_id=shipment.id,
                event_type=ShipmentEventType.NOTE_ADDED,
                occurred_at=datetime.now(UTC),
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_record_shipment_event_rejects_unknown_location() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow.shipments.add(shipment)

    with pytest.raises(ShipmentEventLocationNotFoundError):
        await RecordShipmentEvent(uow).execute(
            RecordShipmentEventCommand(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                event_type=ShipmentEventType.ARRIVED_AT_LOCATION,
                occurred_at=datetime.now(UTC),
                location_id=uuid4(),
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_record_shipment_event_rejects_location_from_other_tenant() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    foreign_location = make_location(
        tenant_id=uuid4(),
    )

    uow.shipments.add(shipment)
    uow.locations.add(foreign_location)

    with pytest.raises(ShipmentEventLocationNotFoundError):
        await RecordShipmentEvent(uow).execute(
            RecordShipmentEventCommand(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                event_type=ShipmentEventType.ARRIVED_AT_LOCATION,
                occurred_at=datetime.now(UTC),
                location_id=foreign_location.id,
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True
