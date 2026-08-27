from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.packages.application.exceptions import PackageNotFoundError
from app.modules.packages.application.use_cases.delete_package import (
    DeletePackage,
    DeletePackageCommand,
)
from app.modules.packages.infrastructure.models.package import Package
from app.modules.shipments.domain.enums import WeightUnit
from tests.unit.packages.fakes import FakeUnitOfWork


def make_package(
    *,
    tenant_id: UUID,
) -> Package:
    package = Package(
        tenant_id=tenant_id,
        shipment_id=uuid4(),
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


async def test_delete_package_soft_deletes_package() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    package = make_package(
        tenant_id=tenant_id,
    )

    uow.packages.add(package)

    await DeletePackage(uow).execute(
        DeletePackageCommand(
            tenant_id=tenant_id,
            package_id=package.id,
        )
    )

    assert package.deleted_at is not None

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False


async def test_delete_package_rejects_unknown_package() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(PackageNotFoundError):
        await DeletePackage(uow).execute(
            DeletePackageCommand(
                tenant_id=uuid4(),
                package_id=uuid4(),
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_delete_package_rejects_package_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    package = make_package(
        tenant_id=uuid4(),
    )

    uow.packages.add(package)

    with pytest.raises(PackageNotFoundError):
        await DeletePackage(uow).execute(
            DeletePackageCommand(
                tenant_id=uuid4(),
                package_id=package.id,
            )
        )

    assert package.deleted_at is None
    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_delete_package_rejects_already_deleted_package() -> None:
    uow = FakeUnitOfWork()
    tenant_id = uuid4()

    package = make_package(
        tenant_id=tenant_id,
    )
    package.deleted_at = datetime.now(UTC)

    uow.packages.add(package)

    with pytest.raises(PackageNotFoundError):
        await DeletePackage(uow).execute(
            DeletePackageCommand(
                tenant_id=tenant_id,
                package_id=package.id,
            )
        )

    assert uow.flushed is False
    assert uow.committed is False
    assert uow.rolled_back is True
