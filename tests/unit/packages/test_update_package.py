from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.packages.application.exceptions import (
    PackageNotFoundError,
    PackageNumberAlreadyExistsError,
    PackageShipmentNotFoundError,
)
from app.modules.packages.application.use_cases.update_package import (
    UpdatePackage,
    UpdatePackageCommand,
)
from app.modules.packages.domain.enums import DimensionUnit
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


def make_package(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
    package_number: str,
) -> Package:
    package = Package(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
        package_number=package_number,
        description="Old description",
        weight=Decimal("1.000"),
        weight_unit=WeightUnit.KG,
        length=Decimal("10.00"),
        width=Decimal("20.00"),
        height=Decimal("30.00"),
        dimension_unit=DimensionUnit.CM,
        notes="Old notes",
    )
    package.id = uuid4()

    return package


def make_command(
    *,
    tenant_id: UUID,
    package_id: UUID,
    shipment_id: UUID,
    package_number: str = "PKG-UPDATED",
) -> UpdatePackageCommand:
    return UpdatePackageCommand(
        tenant_id=tenant_id,
        package_id=package_id,
        shipment_id=shipment_id,
        package_number=package_number,
        description="  Updated description  ",
        weight=Decimal("5.500"),
        weight_unit=WeightUnit.LB,
        length=Decimal("40.00"),
        width=Decimal("30.00"),
        height=Decimal("20.00"),
        dimension_unit=DimensionUnit.IN,
        notes="  Updated notes  ",
    )


async def test_update_package_updates_fields() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
    )

    package = make_package(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        package_number="PKG-001",
    )

    uow.shipments.add(shipment)
    uow.packages.add(package)

    result = await UpdatePackage(uow).execute(
        make_command(
            tenant_id=tenant_id,
            package_id=package.id,
            shipment_id=shipment.id,
        )
    )

    assert result is package

    assert package.shipment_id == shipment.id
    assert package.package_number == "PKG-UPDATED"
    assert package.description == "Updated description"

    assert package.weight == Decimal("5.500")
    assert package.weight_unit == WeightUnit.LB

    assert package.length == Decimal("40.00")
    assert package.width == Decimal("30.00")
    assert package.height == Decimal("20.00")
    assert package.dimension_unit == DimensionUnit.IN

    assert package.notes == "Updated notes"

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_update_package_normalizes_package_number() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
    )

    package = make_package(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        package_number="PKG-001",
    )

    uow.shipments.add(shipment)
    uow.packages.add(package)

    result = await UpdatePackage(uow).execute(
        make_command(
            tenant_id=tenant_id,
            package_id=package.id,
            shipment_id=shipment.id,
            package_number="  pkg-new-001  ",
        )
    )

    assert result.package_number == "PKG-NEW-001"


async def test_update_package_rejects_unknown_package() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
    )

    uow.shipments.add(shipment)

    with pytest.raises(PackageNotFoundError):
        await UpdatePackage(uow).execute(
            make_command(
                tenant_id=tenant_id,
                package_id=uuid4(),
                shipment_id=shipment.id,
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_package_rejects_package_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
    )

    package = make_package(
        tenant_id=uuid4(),
        shipment_id=shipment.id,
        package_number="PKG-001",
    )

    uow.shipments.add(shipment)
    uow.packages.add(package)

    with pytest.raises(PackageNotFoundError):
        await UpdatePackage(uow).execute(
            make_command(
                tenant_id=tenant_id,
                package_id=package.id,
                shipment_id=shipment.id,
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_package_rejects_shipment_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=uuid4(),
        tracking_number="SHIP-001",
    )

    package = make_package(
        tenant_id=tenant_id,
        shipment_id=uuid4(),
        package_number="PKG-001",
    )

    uow.shipments.add(shipment)
    uow.packages.add(package)

    with pytest.raises(PackageShipmentNotFoundError):
        await UpdatePackage(uow).execute(
            make_command(
                tenant_id=tenant_id,
                package_id=package.id,
                shipment_id=shipment.id,
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_package_rejects_duplicate_number_in_target_shipment() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
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

    with pytest.raises(PackageNumberAlreadyExistsError):
        await UpdatePackage(uow).execute(
            make_command(
                tenant_id=tenant_id,
                package_id=second.id,
                shipment_id=shipment.id,
                package_number=" pkg-001 ",
            )
        )

    assert second.package_number == "PKG-002"
    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_package_allows_same_existing_number() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
    )

    package = make_package(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        package_number="PKG-001",
    )

    uow.shipments.add(shipment)
    uow.packages.add(package)

    result = await UpdatePackage(uow).execute(
        make_command(
            tenant_id=tenant_id,
            package_id=package.id,
            shipment_id=shipment.id,
            package_number=" pkg-001 ",
        )
    )

    assert result.package_number == "PKG-001"
    assert uow.committed is True


async def test_update_package_allows_same_number_in_different_shipment() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    first_shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-001",
    )

    second_shipment = make_shipment(
        tenant_id=tenant_id,
        tracking_number="SHIP-002",
    )

    existing = make_package(
        tenant_id=tenant_id,
        shipment_id=first_shipment.id,
        package_number="PKG-001",
    )

    package = make_package(
        tenant_id=tenant_id,
        shipment_id=second_shipment.id,
        package_number="PKG-002",
    )

    uow.shipments.add(first_shipment)
    uow.shipments.add(second_shipment)

    uow.packages.add(existing)
    uow.packages.add(package)

    result = await UpdatePackage(uow).execute(
        make_command(
            tenant_id=tenant_id,
            package_id=package.id,
            shipment_id=second_shipment.id,
            package_number="PKG-001",
        )
    )

    assert result.shipment_id == second_shipment.id
    assert result.package_number == "PKG-001"
    assert uow.committed is True
