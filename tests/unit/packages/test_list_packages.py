from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.packages.application.exceptions import (
    PackageShipmentNotFoundError,
)
from app.modules.packages.application.use_cases.list_packages import (
    ListPackages,
    ListPackagesQuery,
)
from app.modules.packages.infrastructure.models.package import Package
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment
from tests.unit.packages.fakes import FakeUnitOfWork


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
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.KG,
    )
    shipment.id = uuid4()

    return shipment


def make_package(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
    package_number: str,
) -> Package:
    return Package(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
        package_number=package_number,
        description=None,
        weight=Decimal("1.000"),
        weight_unit=WeightUnit.KG,
        length=None,
        width=None,
        height=None,
        dimension_unit=None,
        notes=None,
    )


async def test_list_packages_returns_shipment_packages() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    first = make_package(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        package_number="PKG-001",
    )

    second = make_package(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        package_number="PKG-002",
    )

    uow.shipments.add(shipment)
    uow.packages.add(first)
    uow.packages.add(second)

    result = await ListPackages(uow).execute(
        ListPackagesQuery(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
        )
    )

    assert result == [first, second]


async def test_list_packages_excludes_other_shipments() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    other_shipment = make_shipment(
        tenant_id=tenant_id,
    )
    other_shipment.tracking_number = "SHIP-002"

    expected = make_package(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        package_number="PKG-001",
    )

    other = make_package(
        tenant_id=tenant_id,
        shipment_id=other_shipment.id,
        package_number="PKG-002",
    )

    uow.shipments.add(shipment)
    uow.shipments.add(other_shipment)
    uow.packages.add(expected)
    uow.packages.add(other)

    result = await ListPackages(uow).execute(
        ListPackagesQuery(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
        )
    )

    assert result == [expected]


async def test_list_packages_excludes_soft_deleted_packages() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    active = make_package(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        package_number="PKG-001",
    )

    deleted = make_package(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        package_number="PKG-002",
    )
    deleted.deleted_at = datetime.now(UTC)

    uow.shipments.add(shipment)
    uow.packages.add(active)
    uow.packages.add(deleted)

    result = await ListPackages(uow).execute(
        ListPackagesQuery(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
        )
    )

    assert result == [active]


async def test_list_packages_returns_empty_list() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow.shipments.add(shipment)

    result = await ListPackages(uow).execute(
        ListPackagesQuery(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
        )
    )

    assert result == []


async def test_list_packages_rejects_unknown_shipment() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(PackageShipmentNotFoundError):
        await ListPackages(uow).execute(
            ListPackagesQuery(
                tenant_id=uuid4(),
                shipment_id=uuid4(),
            )
        )

    assert uow.rolled_back is True


async def test_list_packages_rejects_shipment_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    shipment = make_shipment(
        tenant_id=uuid4(),
    )

    uow.shipments.add(shipment)

    with pytest.raises(PackageShipmentNotFoundError):
        await ListPackages(uow).execute(
            ListPackagesQuery(
                tenant_id=uuid4(),
                shipment_id=shipment.id,
            )
        )

    assert uow.rolled_back is True
