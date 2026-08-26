from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.locations.domain.enums import LocationStatus, LocationType
from app.modules.locations.infrastructure.models.location import Location
from app.modules.shipments.application.exceptions import (
    ShipmentCustomerNotFoundError,
    ShipmentDestinationLocationNotFoundError,
    ShipmentNotFoundError,
    ShipmentOriginLocationNotFoundError,
    ShipmentTrackingNumberAlreadyExistsError,
)
from app.modules.shipments.application.use_cases.update_shipment import (
    UpdateShipment,
    UpdateShipmentCommand,
)
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment
from tests.unit.shipments.fakes import FakeUnitOfWork


def make_customer(
    *,
    tenant_id: UUID,
) -> Customer:
    customer = Customer(
        tenant_id=tenant_id,
        name="Acme Trading",
        code="ACME-001",
        status=CustomerStatus.ACTIVE,
    )
    customer.id = uuid4()

    return customer


def make_location(
    *,
    tenant_id: UUID,
    code: str,
) -> Location:
    location = Location(
        tenant_id=tenant_id,
        name=f"Location {code}",
        code=code,
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Industrial Zone",
        status=LocationStatus.ACTIVE,
    )
    location.id = uuid4()

    return location


def make_shipment(
    *,
    tenant_id: UUID,
    customer_id: UUID,
    origin_location_id: UUID,
    destination_location_id: UUID,
    tracking_number: str = "SHIP-001",
) -> Shipment:
    shipment = Shipment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        origin_location_id=origin_location_id,
        destination_location_id=destination_location_id,
        tracking_number=tracking_number,
        status=ShipmentStatus.DRAFT,
        service_type=ServiceType.STANDARD,
        weight=Decimal("1.000"),
        weight_unit=WeightUnit.KG,
    )
    shipment.id = uuid4()

    return shipment


def make_command(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
    customer_id: UUID,
    origin_location_id: UUID,
    destination_location_id: UUID,
    tracking_number: str = "SHIP-002",
) -> UpdateShipmentCommand:
    return UpdateShipmentCommand(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
        customer_id=customer_id,
        origin_location_id=origin_location_id,
        destination_location_id=destination_location_id,
        tracking_number=tracking_number,
        service_type=ServiceType.EXPRESS,
        weight=Decimal("15.750"),
        weight_unit=WeightUnit.KG,
        reference="  ORDER-200  ",
        description="  Updated description  ",
        notes="  Updated notes  ",
    )


async def test_update_shipment_updates_fields() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    customer = make_customer(tenant_id=tenant_id)
    origin = make_location(tenant_id=tenant_id, code="ORIGIN")
    destination = make_location(tenant_id=tenant_id, code="DEST")

    shipment = make_shipment(
        tenant_id=tenant_id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
    )

    uow.customers.add(customer)
    uow.locations.add(origin)
    uow.locations.add(destination)
    uow.shipments.add(shipment)

    result = await UpdateShipment(uow).execute(
        make_command(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number="  ship-002  ",
        )
    )

    assert result is shipment
    assert shipment.tracking_number == "SHIP-002"
    assert shipment.service_type == ServiceType.EXPRESS
    assert shipment.weight == Decimal("15.750")
    assert shipment.weight_unit == WeightUnit.KG
    assert shipment.reference == "ORDER-200"
    assert shipment.description == "Updated description"
    assert shipment.notes == "Updated notes"

    assert shipment.status == ShipmentStatus.DRAFT

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_update_shipment_rejects_unknown_shipment() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(ShipmentNotFoundError):
        await UpdateShipment(uow).execute(
            make_command(
                tenant_id=uuid4(),
                shipment_id=uuid4(),
                customer_id=uuid4(),
                origin_location_id=uuid4(),
                destination_location_id=uuid4(),
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_shipment_rejects_shipment_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    shipment = make_shipment(
        tenant_id=uuid4(),
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
    )

    uow.shipments.add(shipment)

    with pytest.raises(ShipmentNotFoundError):
        await UpdateShipment(uow).execute(
            make_command(
                tenant_id=uuid4(),
                shipment_id=shipment.id,
                customer_id=uuid4(),
                origin_location_id=uuid4(),
                destination_location_id=uuid4(),
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_shipment_rejects_duplicate_tracking_number() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    customer = make_customer(tenant_id=tenant_id)
    origin = make_location(tenant_id=tenant_id, code="ORIGIN")
    destination = make_location(tenant_id=tenant_id, code="DEST")

    first = make_shipment(
        tenant_id=tenant_id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number="SHIP-001",
    )

    second = make_shipment(
        tenant_id=tenant_id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number="SHIP-002",
    )

    uow.customers.add(customer)
    uow.locations.add(origin)
    uow.locations.add(destination)
    uow.shipments.add(first)
    uow.shipments.add(second)

    with pytest.raises(ShipmentTrackingNumberAlreadyExistsError):
        await UpdateShipment(uow).execute(
            make_command(
                tenant_id=tenant_id,
                shipment_id=second.id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
                tracking_number=" ship-001 ",
            )
        )

    assert second.tracking_number == "SHIP-002"
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_shipment_allows_same_tracking_number() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    customer = make_customer(tenant_id=tenant_id)
    origin = make_location(tenant_id=tenant_id, code="ORIGIN")
    destination = make_location(tenant_id=tenant_id, code="DEST")

    shipment = make_shipment(
        tenant_id=tenant_id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        tracking_number="SHIP-001",
    )

    uow.customers.add(customer)
    uow.locations.add(origin)
    uow.locations.add(destination)
    uow.shipments.add(shipment)

    result = await UpdateShipment(uow).execute(
        make_command(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number=" ship-001 ",
        )
    )

    assert result.tracking_number == "SHIP-001"
    assert uow.committed is True


async def test_update_shipment_rejects_customer_from_other_tenant() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    customer = make_customer(tenant_id=uuid4())
    origin = make_location(tenant_id=tenant_id, code="ORIGIN")
    destination = make_location(tenant_id=tenant_id, code="DEST")

    shipment = make_shipment(
        tenant_id=tenant_id,
        customer_id=uuid4(),
        origin_location_id=origin.id,
        destination_location_id=destination.id,
    )

    uow.shipments.add(shipment)
    uow.customers.add(customer)
    uow.locations.add(origin)
    uow.locations.add(destination)

    with pytest.raises(ShipmentCustomerNotFoundError):
        await UpdateShipment(uow).execute(
            make_command(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_shipment_rejects_origin_from_other_tenant() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    customer = make_customer(tenant_id=tenant_id)
    origin = make_location(tenant_id=uuid4(), code="ORIGIN")
    destination = make_location(tenant_id=tenant_id, code="DEST")

    shipment = make_shipment(
        tenant_id=tenant_id,
        customer_id=customer.id,
        origin_location_id=uuid4(),
        destination_location_id=destination.id,
    )

    uow.shipments.add(shipment)
    uow.customers.add(customer)
    uow.locations.add(origin)
    uow.locations.add(destination)

    with pytest.raises(ShipmentOriginLocationNotFoundError):
        await UpdateShipment(uow).execute(
            make_command(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_shipment_rejects_destination_from_other_tenant() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    customer = make_customer(tenant_id=tenant_id)
    origin = make_location(tenant_id=tenant_id, code="ORIGIN")
    destination = make_location(tenant_id=uuid4(), code="DEST")

    shipment = make_shipment(
        tenant_id=tenant_id,
        customer_id=customer.id,
        origin_location_id=origin.id,
        destination_location_id=uuid4(),
    )

    uow.shipments.add(shipment)
    uow.customers.add(customer)
    uow.locations.add(origin)
    uow.locations.add(destination)

    with pytest.raises(ShipmentDestinationLocationNotFoundError):
        await UpdateShipment(uow).execute(
            make_command(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True
