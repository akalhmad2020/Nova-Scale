from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.locations.application.exceptions import LocationNotFoundError
from app.modules.locations.application.use_cases.get_location import (
    GetLocation,
    GetLocationQuery,
)
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location
from tests.unit.locations.fakes import FakeUnitOfWork


async def test_get_location_returns_location() -> None:
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

    use_case = GetLocation(uow)

    result = await use_case.execute(
        GetLocationQuery(
            tenant_id=tenant_id,
            location_id=location.id,
        )
    )

    assert result is location


async def test_get_location_rejects_unknown_location() -> None:
    uow = FakeUnitOfWork()

    use_case = GetLocation(uow)

    with pytest.raises(LocationNotFoundError):
        await use_case.execute(
            GetLocationQuery(
                tenant_id=uuid4(),
                location_id=uuid4(),
            )
        )

    assert uow.rolled_back is True


async def test_get_location_rejects_location_from_other_tenant() -> None:
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

    use_case = GetLocation(uow)

    with pytest.raises(LocationNotFoundError):
        await use_case.execute(
            GetLocationQuery(
                tenant_id=uuid4(),
                location_id=location.id,
            )
        )

    assert uow.rolled_back is True


async def test_get_location_rejects_soft_deleted_location() -> None:
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
    location.deleted_at = datetime.now(UTC)

    uow.locations.add(location)

    use_case = GetLocation(uow)

    with pytest.raises(LocationNotFoundError):
        await use_case.execute(
            GetLocationQuery(
                tenant_id=tenant_id,
                location_id=location.id,
            )
        )

    assert uow.rolled_back is True
