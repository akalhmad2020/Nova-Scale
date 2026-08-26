from datetime import UTC, datetime
from uuid import uuid4

from app.modules.locations.application.use_cases.list_locations import (
    ListLocations,
    ListLocationsQuery,
)
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location
from tests.unit.locations.fakes import FakeUnitOfWork


async def test_list_locations_returns_tenant_locations() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    first = Location(
        tenant_id=tenant_id,
        name="First Warehouse",
        code="WH-001",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="First Address",
        status=LocationStatus.ACTIVE,
    )

    second = Location(
        tenant_id=tenant_id,
        name="Second Warehouse",
        code="WH-002",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Nablus",
        address_line1="Second Address",
        status=LocationStatus.ACTIVE,
    )

    uow.locations.add(first)
    uow.locations.add(second)

    use_case = ListLocations(uow)

    result = await use_case.execute(
        ListLocationsQuery(
            tenant_id=tenant_id,
        )
    )

    assert result == [first, second]


async def test_list_locations_excludes_other_tenants() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    expected = Location(
        tenant_id=tenant_id,
        name="Expected Warehouse",
        code="WH-001",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Expected Address",
        status=LocationStatus.ACTIVE,
    )

    other = Location(
        tenant_id=uuid4(),
        name="Other Warehouse",
        code="WH-002",
        type=LocationType.WAREHOUSE,
        country_code="JO",
        city="Amman",
        address_line1="Other Address",
        status=LocationStatus.ACTIVE,
    )

    uow.locations.add(expected)
    uow.locations.add(other)

    use_case = ListLocations(uow)

    result = await use_case.execute(
        ListLocationsQuery(
            tenant_id=tenant_id,
        )
    )

    assert result == [expected]


async def test_list_locations_excludes_soft_deleted_locations() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    active = Location(
        tenant_id=tenant_id,
        name="Active Warehouse",
        code="WH-001",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Active Address",
        status=LocationStatus.ACTIVE,
    )

    deleted = Location(
        tenant_id=tenant_id,
        name="Deleted Warehouse",
        code="WH-002",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Deleted Address",
        status=LocationStatus.ACTIVE,
    )
    deleted.deleted_at = datetime.now(UTC)

    uow.locations.add(active)
    uow.locations.add(deleted)

    use_case = ListLocations(uow)

    result = await use_case.execute(
        ListLocationsQuery(
            tenant_id=tenant_id,
        )
    )

    assert result == [active]


async def test_list_locations_returns_empty_list() -> None:
    uow = FakeUnitOfWork()

    use_case = ListLocations(uow)

    result = await use_case.execute(
        ListLocationsQuery(
            tenant_id=uuid4(),
        )
    )

    assert result == []
