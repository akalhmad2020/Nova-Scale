from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.packages.application.exceptions import (
    PackageNumberAlreadyExistsError,
    PackageShipmentNotFoundError,
)
from app.modules.packages.application.use_cases.create_package import (
    CreatePackage,
    CreatePackageCommand,
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
    tracking_number: str = "SHIP-001",
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


def make_command(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
    package_number: str = "PKG-001",
) -> CreatePackageCommand:
    return CreatePackageCommand(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
        package_number=package_number,
        description="  Electronics  ",
        weight=Decimal("4.500"),
        weight_unit=WeightUnit.KG,
        length=Decimal("40.00"),
        width=Decimal("30.00"),
        height=Decimal("20.00"),
        dimension_unit=DimensionUnit.CM,
        notes="  Fragile  ",
    )


async def test_create_package_creates_package() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow.shipments.add(shipment)

    result = await CreatePackage(uow).execute(
        make_command(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
        )
    )

    assert result.tenant_id == tenant_id
    assert result.shipment_id == shipment.id
    assert result.package_number == "PKG-001"

    assert result.description == "Electronics"
    assert result.weight == Decimal("4.500")
    assert result.weight_unit == WeightUnit.KG

    assert result.length == Decimal("40.00")
    assert result.width == Decimal("30.00")
    assert result.height == Decimal("20.00")
    assert result.dimension_unit == DimensionUnit.CM

    assert result.notes == "Fragile"

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_create_package_normalizes_package_number() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    uow.shipments.add(shipment)

    result = await CreatePackage(uow).execute(
        make_command(
            tenant_id=tenant_id,
            shipment_id=shipment.id,
            package_number="  pkg-abc-001  ",
        )
    )

    assert result.package_number == "PKG-ABC-001"


async def test_create_package_rejects_unknown_shipment() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(PackageShipmentNotFoundError):
        await CreatePackage(uow).execute(
            make_command(
                tenant_id=uuid4(),
                shipment_id=uuid4(),
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_package_rejects_shipment_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    shipment = make_shipment(
        tenant_id=uuid4(),
    )

    uow.shipments.add(shipment)

    with pytest.raises(PackageShipmentNotFoundError):
        await CreatePackage(uow).execute(
            make_command(
                tenant_id=uuid4(),
                shipment_id=shipment.id,
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_package_rejects_duplicate_number_in_same_shipment() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    shipment = make_shipment(
        tenant_id=tenant_id,
    )

    existing = Package(
        tenant_id=tenant_id,
        shipment_id=shipment.id,
        package_number="PKG-001",
        description=None,
        weight=Decimal("1.000"),
        weight_unit=WeightUnit.KG,
        length=None,
        width=None,
        height=None,
        dimension_unit=None,
        notes=None,
    )

    uow.shipments.add(shipment)
    uow.packages.add(existing)

    with pytest.raises(PackageNumberAlreadyExistsError):
        await CreatePackage(uow).execute(
            make_command(
                tenant_id=tenant_id,
                shipment_id=shipment.id,
                package_number=" pkg-001 ",
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_package_allows_same_number_in_different_shipment() -> None:
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

    existing = Package(
        tenant_id=tenant_id,
        shipment_id=first_shipment.id,
        package_number="PKG-001",
        description=None,
        weight=Decimal("1.000"),
        weight_unit=WeightUnit.KG,
        length=None,
        width=None,
        height=None,
        dimension_unit=None,
        notes=None,
    )

    uow.shipments.add(first_shipment)
    uow.shipments.add(second_shipment)
    uow.packages.add(existing)

    result = await CreatePackage(uow).execute(
        make_command(
            tenant_id=tenant_id,
            shipment_id=second_shipment.id,
            package_number="PKG-001",
        )
    )

    assert result.shipment_id == second_shipment.id
    assert result.package_number == "PKG-001"
    assert uow.committed is True
