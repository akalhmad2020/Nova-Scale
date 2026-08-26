from uuid import uuid4

import pytest

from app.modules.locations.application.exceptions import LocationNotFoundError
from app.modules.locations.application.use_cases.delete_location import (
    DeleteLocation,
    DeleteLocationCommand,
)
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location
from tests.unit.locations.fakes import FakeUnitOfWork


async def test_delete_location_soft_deletes_location() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    location = Location(
        tenant_id=tenant_id,
        name="Main Warehouse",
        code="WH-001",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Industrial Zone",
        status=LocationStatus.ACTIVE,
    )
    location.id = uuid4()

    uow.locations.add(location)

    use_case = DeleteLocation(uow)

    await use_case.execute(
        DeleteLocationCommand(
            tenant_id=tenant_id,
            location_id=location.id,
        )
    )

    assert location.deleted_at is not None

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False


async def test_delete_location_rejects_unknown_location() -> None:
    uow = FakeUnitOfWork()

    use_case = DeleteLocation(uow)

    with pytest.raises(LocationNotFoundError):
        await use_case.execute(
            DeleteLocationCommand(
                tenant_id=uuid4(),
                location_id=uuid4(),
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_delete_location_rejects_location_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    location = Location(
        tenant_id=uuid4(),
        name="Foreign Warehouse",
        code="WH-001",
        type=LocationType.WAREHOUSE,
        country_code="JO",
        city="Amman",
        address_line1="Industrial Area",
        status=LocationStatus.ACTIVE,
    )
    location.id = uuid4()

    uow.locations.add(location)

    use_case = DeleteLocation(uow)

    with pytest.raises(LocationNotFoundError):
        await use_case.execute(
            DeleteLocationCommand(
                tenant_id=uuid4(),
                location_id=location.id,
            )
        )

    assert location.deleted_at is None
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_delete_location_rejects_already_deleted_location() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    location = Location(
        tenant_id=tenant_id,
        name="Deleted Warehouse",
        code="WH-001",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Industrial Zone",
        status=LocationStatus.ACTIVE,
    )
    location.id = uuid4()

    uow.locations.add(location)

    use_case = DeleteLocation(uow)

    await use_case.execute(
        DeleteLocationCommand(
            tenant_id=tenant_id,
            location_id=location.id,
        )
    )

    first_deleted_at = location.deleted_at

    with pytest.raises(LocationNotFoundError):
        await use_case.execute(
            DeleteLocationCommand(
                tenant_id=tenant_id,
                location_id=location.id,
            )
        )

    assert location.deleted_at == first_deleted_at
