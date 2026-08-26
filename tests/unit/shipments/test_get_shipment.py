from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.shipments.application.exceptions import ShipmentNotFoundError
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
from tests.unit.shipments.fakes import FakeUnitOfWork


def make_shipment(
    *,
    tenant_id: UUID,
) -> Shipment:
    shipment = Shipment(
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
    shipment.id = uuid4()

    return shipment


async def test_get_shipment_returns_shipment() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow.shipments.add(shipment)

    result = await GetShipment(uow).execute(
        GetShipmentQuery(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
        )
    )

    assert result is shipment


async def test_get_shipment_rejects_unknown_shipment() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(ShipmentNotFoundError):
        await GetShipment(uow).execute(
            GetShipmentQuery(
                tenant_id=uuid4(),
                shipment_id=uuid4(),
            )
        )

    assert uow.rolled_back is True


async def test_get_shipment_rejects_shipment_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    shipment = make_shipment(
        tenant_id=uuid4(),
    )

    uow.shipments.add(shipment)

    with pytest.raises(ShipmentNotFoundError):
        await GetShipment(uow).execute(
            GetShipmentQuery(
                tenant_id=uuid4(),
                shipment_id=shipment.id,
            )
        )

    assert uow.rolled_back is True


async def test_get_shipment_rejects_soft_deleted_shipment() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )
    shipment.deleted_at = datetime.now(UTC)

    uow.shipments.add(shipment)

    with pytest.raises(ShipmentNotFoundError):
        await GetShipment(uow).execute(
            GetShipmentQuery(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
            )
        )

    assert uow.rolled_back is True
