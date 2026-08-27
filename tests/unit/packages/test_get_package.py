from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.packages.application.exceptions import PackageNotFoundError
from app.modules.packages.application.use_cases.get_package import (
    GetPackage,
    GetPackageQuery,
)
from app.modules.packages.infrastructure.models.package import Package
from app.modules.shipments.domain.enums import WeightUnit
from tests.unit.packages.fakes import FakeUnitOfWork


def make_package(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
) -> Package:
    package = Package(
        tenant_id=tenant_id,
        shipment_id=shipment_id,
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
    package.id = uuid4()

    return package


async def test_get_package_returns_package() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    package = make_package(
        tenant_id=tenant_id,
        shipment_id=uuid4(),
    )

    uow.packages.add(package)

    result = await GetPackage(uow).execute(
        GetPackageQuery(
            tenant_id=tenant_id,
            package_id=package.id,
        )
    )

    assert result is package


async def test_get_package_rejects_unknown_package() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(PackageNotFoundError):
        await GetPackage(uow).execute(
            GetPackageQuery(
                tenant_id=uuid4(),
                package_id=uuid4(),
            )
        )

    assert uow.rolled_back is True


async def test_get_package_rejects_other_tenant_package() -> None:
    uow = FakeUnitOfWork()

    package = make_package(
        tenant_id=uuid4(),
        shipment_id=uuid4(),
    )

    uow.packages.add(package)

    with pytest.raises(PackageNotFoundError):
        await GetPackage(uow).execute(
            GetPackageQuery(
                tenant_id=uuid4(),
                package_id=package.id,
            )
        )

    assert uow.rolled_back is True


async def test_get_package_rejects_soft_deleted_package() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    package = make_package(
        tenant_id=tenant_id,
        shipment_id=uuid4(),
    )
    package.deleted_at = datetime.now(UTC)

    uow.packages.add(package)

    with pytest.raises(PackageNotFoundError):
        await GetPackage(uow).execute(
            GetPackageQuery(
                tenant_id=tenant_id,
                package_id=package.id,
            )
        )

    assert uow.rolled_back is True
