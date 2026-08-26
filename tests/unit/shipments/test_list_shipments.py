from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.modules.shipments.application.use_cases.list_shipments import (
    ListShipments,
    ListShipmentsQuery,
)
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment
from tests.unit.shipments.fakes import FakeUnitOfWork


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
        weight=Decimal("1.000"),
        weight_unit=WeightUnit.KG,
    )

    return shipment


async def test_list_shipments_returns_tenant_shipments() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    first = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
    )

    second = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-002",
    )

    uow.shipments.add(first)
    uow.shipments.add(second)

    result = await ListShipments(uow).execute(
        ListShipmentsQuery(
            tenant_id=tenant_id,
        )
    )

    assert result == [first, second]


async def test_list_shipments_excludes_other_tenants() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    expected = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
    )

    other = make_shipment(
        tenant_id=uuid4(),
        tracking_number="SHIP-002",
    )

    uow.shipments.add(expected)
    uow.shipments.add(other)

    result = await ListShipments(uow).execute(
        ListShipmentsQuery(
            tenant_id=tenant_id,
        )
    )

    assert result == [expected]


async def test_list_shipments_excludes_soft_deleted_shipments() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    active = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
    )

    deleted = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-002",
    )
    deleted.deleted_at = datetime.now(UTC)

    uow.shipments.add(active)
    uow.shipments.add(deleted)

    result = await ListShipments(uow).execute(
        ListShipmentsQuery(
            tenant_id=tenant_id,
        )
    )

    assert result == [active]


async def test_list_shipments_returns_empty_list() -> None:
    uow = FakeUnitOfWork()

    result = await ListShipments(uow).execute(
        ListShipmentsQuery(
            tenant_id=uuid4(),
        )
    )

    assert result == []
