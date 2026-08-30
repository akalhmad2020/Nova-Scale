from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.locations.domain.enums import LocationStatus, LocationType
from app.modules.locations.infrastructure.models.location import Location
from app.modules.shipments.application.exceptions import (
    ShipmentCustomerNotFoundError,
    ShipmentDestinationLocationNotFoundError,
    ShipmentOriginLocationNotFoundError,
    ShipmentTrackingNumberAlreadyExistsError,
)
from app.modules.shipments.application.use_cases.create_shipment import (
    CreateShipment,
    CreateShipmentCommand,
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


def make_command(
    *,
    tenant_id: UUID,
    customer_id: UUID,
    origin_location_id: UUID,
    destination_location_id: UUID,
    tracking_number: str = "SHIP-001",
    actor_id: UUID | None = None,
) -> CreateShipmentCommand:
    return CreateShipmentCommand(
        tenant_id=tenant_id,
        actor_id=actor_id or uuid4(),
        customer_id=customer_id,
        origin_location_id=origin_location_id,
        destination_location_id=destination_location_id,
        tracking_number=tracking_number,
        service_type=ServiceType.EXPRESS,
        weight=Decimal("12.500"),
        weight_unit=WeightUnit.KG,
        reference="  ORDER-100  ",
        description="  Electronics  ",
        notes="  Handle carefully  ",
    )


async def test_create_shipment_creates_draft_shipment() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()
    actor_id = uuid4()

    customer = make_customer(tenant_id=tenant_id)

    origin = make_location(
        tenant_id=tenant_id,
        code="ORIGIN-001",
    )

    destination = make_location(
        tenant_id=tenant_id,
        code="DEST-001",
    )

    uow.customers.add(customer)
    uow.locations.add(origin)
    uow.locations.add(destination)

    use_case = CreateShipment(uow)

    result = await use_case.execute(
        make_command(
            tenant_id=tenant_id,
            actor_id=actor_id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
        )
    )

    assert result.tenant_id == tenant_id
    assert result.customer_id == customer.id
    assert result.origin_location_id == origin.id
    assert result.destination_location_id == destination.id

    assert result.tracking_number == "SHIP-001"
    assert result.status == ShipmentStatus.DRAFT
    assert result.service_type == ServiceType.EXPRESS
    assert result.weight == Decimal("12.500")
    assert result.weight_unit == WeightUnit.KG

    assert result.reference == "ORDER-100"
    assert result.description == "Electronics"
    assert result.notes == "Handle carefully"

    assert result.id is not None

    assert len(uow.audit_logs.items) == 1

    audit_log = uow.audit_logs.items[0]

    assert audit_log.tenant_id == tenant_id
    assert audit_log.actor_type == AuditActorType.USER
    assert audit_log.actor_id == actor_id
    assert audit_log.action == "shipment.created"
    assert audit_log.resource_type == "shipment"
    assert audit_log.resource_id == result.id
    assert audit_log.outcome == AuditOutcome.SUCCESS
    assert audit_log.metadata_ == {
        "tracking_number": "SHIP-001",
        "customer_id": str(customer.id),
        "origin_location_id": str(origin.id),
        "destination_location_id": str(destination.id),
        "service_type": ServiceType.EXPRESS.value,
        "weight": "12.500",
        "weight_unit": WeightUnit.KG.value,
    }

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_create_shipment_normalizes_tracking_number() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    customer = make_customer(tenant_id=tenant_id)
    origin = make_location(tenant_id=tenant_id, code="ORIGIN")
    destination = make_location(tenant_id=tenant_id, code="DEST")

    uow.customers.add(customer)
    uow.locations.add(origin)
    uow.locations.add(destination)

    result = await CreateShipment(uow).execute(
        make_command(
            tenant_id=tenant_id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number="  ship-abc-001  ",
        )
    )

    assert result.tracking_number == "SHIP-ABC-001"


async def test_create_shipment_rejects_duplicate_tracking_number() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    existing = Shipment(
        tenant_id=tenant_id,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        tracking_number="SHIP-001",
        status=ShipmentStatus.DRAFT,
        service_type=ServiceType.STANDARD,
        weight=Decimal("1.000"),
        weight_unit=WeightUnit.KG,
    )

    uow.shipments.add(existing)

    use_case = CreateShipment(uow)

    with pytest.raises(ShipmentTrackingNumberAlreadyExistsError):
        await use_case.execute(
            make_command(
                tenant_id=tenant_id,
                customer_id=uuid4(),
                origin_location_id=uuid4(),
                destination_location_id=uuid4(),
                tracking_number=" ship-001 ",
            )
        )

    assert uow.audit_logs.items == []
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_shipment_rejects_customer_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    other_tenant_id = uuid4()

    customer = make_customer(
        tenant_id=other_tenant_id,
    )

    origin = make_location(
        tenant_id=tenant_id,
        code="ORIGIN",
    )

    destination = make_location(
        tenant_id=tenant_id,
        code="DEST",
    )

    uow.customers.add(customer)
    uow.locations.add(origin)
    uow.locations.add(destination)

    with pytest.raises(ShipmentCustomerNotFoundError):
        await CreateShipment(uow).execute(
            make_command(
                tenant_id=tenant_id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
            )
        )

    assert uow.audit_logs.items == []
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_shipment_rejects_origin_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    customer = make_customer(tenant_id=tenant_id)

    origin = make_location(
        tenant_id=uuid4(),
        code="ORIGIN",
    )

    destination = make_location(
        tenant_id=tenant_id,
        code="DEST",
    )

    uow.customers.add(customer)
    uow.locations.add(origin)
    uow.locations.add(destination)

    with pytest.raises(ShipmentOriginLocationNotFoundError):
        await CreateShipment(uow).execute(
            make_command(
                tenant_id=tenant_id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
            )
        )

    assert uow.audit_logs.items == []
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_shipment_rejects_destination_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    customer = make_customer(tenant_id=tenant_id)

    origin = make_location(
        tenant_id=tenant_id,
        code="ORIGIN",
    )

    destination = make_location(
        tenant_id=uuid4(),
        code="DEST",
    )

    uow.customers.add(customer)
    uow.locations.add(origin)
    uow.locations.add(destination)

    with pytest.raises(ShipmentDestinationLocationNotFoundError):
        await CreateShipment(uow).execute(
            make_command(
                tenant_id=tenant_id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
            )
        )

    assert uow.audit_logs.items == []
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_shipment_allows_same_tracking_number_in_other_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    other_tenant_id = uuid4()

    existing = Shipment(
        tenant_id=other_tenant_id,
        customer_id=uuid4(),
        origin_location_id=uuid4(),
        destination_location_id=uuid4(),
        tracking_number="SHIP-001",
        status=ShipmentStatus.DRAFT,
        service_type=ServiceType.STANDARD,
        weight=Decimal("1.000"),
        weight_unit=WeightUnit.KG,
    )

    uow.shipments.add(existing)

    customer = make_customer(tenant_id=tenant_id)
    origin = make_location(tenant_id=tenant_id, code="ORIGIN")
    destination = make_location(tenant_id=tenant_id, code="DEST")

    uow.customers.add(customer)
    uow.locations.add(origin)
    uow.locations.add(destination)

    result = await CreateShipment(uow).execute(
        make_command(
            tenant_id=tenant_id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number="SHIP-001",
        )
    )

    assert result.tracking_number == "SHIP-001"
    assert result.tenant_id == tenant_id

    assert len(uow.audit_logs.items) == 1
    assert uow.audit_logs.items[0].action == "shipment.created"

    assert uow.committed is True
