from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.locations.application.exceptions import (
    LocationCodeAlreadyExistsError,
    LocationNotFoundError,
)
from app.modules.locations.application.use_cases.update_location import (
    UpdateLocation,
    UpdateLocationCommand,
)
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location
from tests.unit.locations.fakes import FakeUnitOfWork


def make_location(
    *,
    tenant_id: UUID | None = None,
    code: str = "WH-001",
) -> Location:
    location = Location(
        tenant_id=tenant_id or uuid4(),
        name="Old Warehouse",
        code=code,
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Old Address",
        status=LocationStatus.ACTIVE,
    )
    location.id = uuid4()

    return location


async def test_update_location_updates_fields() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    location = make_location(tenant_id=tenant_id)

    uow.locations.add(location)

    use_case = UpdateLocation(uow)

    result = await use_case.execute(
        UpdateLocationCommand(
            tenant_id=tenant_id,
            location_id=location.id,
            name="  New Warehouse  ",
            code="  wh-002  ",
            type=LocationType.PICKUP,
            country_code="  jo  ",
            state="  Amman  ",
            city="  Amman  ",
            postal_code="  11118  ",
            address_line1="  New Address  ",
            address_line2="  Building 10  ",
            contact_name="  Operations  ",
            email="  OPS@EXAMPLE.COM  ",
            phone="  +962790000000  ",
            latitude=Decimal("31.953900"),
            longitude=Decimal("35.910600"),
            notes="  Updated location  ",
        )
    )

    assert result is location
    assert location.name == "New Warehouse"
    assert location.code == "WH-002"
    assert location.type is LocationType.PICKUP
    assert location.country_code == "JO"
    assert location.state == "Amman"
    assert location.city == "Amman"
    assert location.postal_code == "11118"
    assert location.address_line1 == "New Address"
    assert location.address_line2 == "Building 10"
    assert location.contact_name == "Operations"
    assert location.email == "ops@example.com"
    assert location.phone == "+962790000000"
    assert location.latitude == Decimal("31.953900")
    assert location.longitude == Decimal("35.910600")
    assert location.notes == "Updated location"

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_update_location_rejects_unknown_location() -> None:
    uow = FakeUnitOfWork()

    use_case = UpdateLocation(uow)

    with pytest.raises(LocationNotFoundError):
        await use_case.execute(
            UpdateLocationCommand(
                tenant_id=uuid4(),
                location_id=uuid4(),
                name="Warehouse",
                code="WH-001",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Address",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_location_rejects_location_from_other_tenant() -> None:
    uow = FakeUnitOfWork()

    location = make_location()

    uow.locations.add(location)

    use_case = UpdateLocation(uow)

    with pytest.raises(LocationNotFoundError):
        await use_case.execute(
            UpdateLocationCommand(
                tenant_id=uuid4(),
                location_id=location.id,
                name="Updated Warehouse",
                code="WH-002",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Updated Address",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_location_rejects_duplicate_code() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    first = make_location(
        tenant_id=tenant_id,
        code="WH-001",
    )
    second = make_location(
        tenant_id=tenant_id,
        code="WH-002",
    )

    uow.locations.add(first)
    uow.locations.add(second)

    use_case = UpdateLocation(uow)

    with pytest.raises(LocationCodeAlreadyExistsError):
        await use_case.execute(
            UpdateLocationCommand(
                tenant_id=tenant_id,
                location_id=second.id,
                name="Second Warehouse",
                code=" wh-001 ",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Address",
            )
        )

    assert second.code == "WH-002"
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_location_allows_same_existing_code() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    location = make_location(
        tenant_id=tenant_id,
        code="WH-001",
    )

    uow.locations.add(location)

    use_case = UpdateLocation(uow)

    result = await use_case.execute(
        UpdateLocationCommand(
            tenant_id=tenant_id,
            location_id=location.id,
            name="Updated Warehouse",
            code=" wh-001 ",
            type=LocationType.WAREHOUSE,
            country_code="PS",
            city="Ramallah",
            address_line1="Updated Address",
        )
    )

    assert result.code == "WH-001"
    assert result.name == "Updated Warehouse"
    assert uow.committed is True
