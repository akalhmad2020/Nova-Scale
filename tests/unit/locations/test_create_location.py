from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.locations.application.exceptions import (
    LocationCodeAlreadyExistsError,
)
from app.modules.locations.application.use_cases.create_location import (
    CreateLocation,
    CreateLocationCommand,
)
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location
from tests.unit.locations.fakes import FakeUnitOfWork


async def test_create_location_creates_active_location() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    use_case = CreateLocation(uow)

    location = await use_case.execute(
        CreateLocationCommand(
            tenant_id=tenant_id,
            name="Main Warehouse",
            code="WH-001",
            type=LocationType.WAREHOUSE,
            country_code="PS",
            city="Ramallah",
            address_line1="Industrial Zone",
            latitude=Decimal("31.903800"),
            longitude=Decimal("35.203400"),
        )
    )

    assert location.tenant_id == tenant_id
    assert location.name == "Main Warehouse"
    assert location.code == "WH-001"
    assert location.type is LocationType.WAREHOUSE
    assert location.country_code == "PS"
    assert location.city == "Ramallah"
    assert location.address_line1 == "Industrial Zone"
    assert location.status is LocationStatus.ACTIVE

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_create_location_normalizes_fields() -> None:
    uow = FakeUnitOfWork()

    use_case = CreateLocation(uow)

    location = await use_case.execute(
        CreateLocationCommand(
            tenant_id=uuid4(),
            name="  Main Warehouse  ",
            code="  wh-001  ",
            type=LocationType.WAREHOUSE,
            country_code="  ps  ",
            state="  Ramallah and Al-Bireh  ",
            city="  Ramallah  ",
            postal_code="  P600  ",
            address_line1="  Industrial Zone  ",
            address_line2="  Building 5  ",
            contact_name="  Operations Team  ",
            email="  OPS@EXAMPLE.COM  ",
            phone="  +970599000000  ",
            notes="  Main distribution location  ",
        )
    )

    assert location.name == "Main Warehouse"
    assert location.code == "WH-001"
    assert location.country_code == "PS"
    assert location.state == "Ramallah and Al-Bireh"
    assert location.city == "Ramallah"
    assert location.postal_code == "P600"
    assert location.address_line1 == "Industrial Zone"
    assert location.address_line2 == "Building 5"
    assert location.contact_name == "Operations Team"
    assert location.email == "ops@example.com"
    assert location.phone == "+970599000000"
    assert location.notes == "Main distribution location"


async def test_create_location_rejects_duplicate_code_in_same_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    existing = Location(
        tenant_id=tenant_id,
        name="Existing Warehouse",
        code="WH-001",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="Existing Address",
        status=LocationStatus.ACTIVE,
    )

    uow.locations.add(existing)

    use_case = CreateLocation(uow)

    with pytest.raises(LocationCodeAlreadyExistsError):
        await use_case.execute(
            CreateLocationCommand(
                tenant_id=tenant_id,
                name="Another Warehouse",
                code=" wh-001 ",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Another Address",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_location_allows_same_code_in_different_tenant() -> None:
    uow = FakeUnitOfWork()

    first_tenant_id = uuid4()
    second_tenant_id = uuid4()

    existing = Location(
        tenant_id=first_tenant_id,
        name="First Tenant Warehouse",
        code="WH-001",
        type=LocationType.WAREHOUSE,
        country_code="PS",
        city="Ramallah",
        address_line1="First Address",
        status=LocationStatus.ACTIVE,
    )

    uow.locations.add(existing)

    use_case = CreateLocation(uow)

    location = await use_case.execute(
        CreateLocationCommand(
            tenant_id=second_tenant_id,
            name="Second Tenant Warehouse",
            code="WH-001",
            type=LocationType.WAREHOUSE,
            country_code="JO",
            city="Amman",
            address_line1="Second Address",
        )
    )

    assert location.tenant_id == second_tenant_id
    assert location.code == "WH-001"

    assert uow.committed is True
    assert uow.rolled_back is False


async def test_create_location_preserves_coordinates() -> None:
    uow = FakeUnitOfWork()

    latitude = Decimal("31.903800")
    longitude = Decimal("35.203400")

    use_case = CreateLocation(uow)

    location = await use_case.execute(
        CreateLocationCommand(
            tenant_id=uuid4(),
            name="Geo Warehouse",
            code="GEO-001",
            type=LocationType.WAREHOUSE,
            country_code="PS",
            city="Ramallah",
            address_line1="Industrial Zone",
            latitude=latitude,
            longitude=longitude,
        )
    )

    assert location.latitude == latitude
    assert location.longitude == longitude
