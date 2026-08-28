from uuid import uuid4

import pytest

from app.modules.carriers.application.exceptions import (
    CarrierCodeAlreadyExistsError,
)
from app.modules.carriers.application.use_cases.create_carrier import (
    CreateCarrier,
    CreateCarrierCommand,
)
from app.modules.carriers.domain.enums import CarrierStatus
from app.modules.carriers.infrastructure.models.carrier import Carrier
from tests.unit.carriers.fakes import FakeUnitOfWork


async def test_create_carrier_creates_active_carrier() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    result = await CreateCarrier(uow).execute(
        CreateCarrierCommand(
            tenant_id=tenant_id,
            code="  dhl  ",
            name="  DHL Express  ",
        )
    )

    assert result.tenant_id == tenant_id
    assert result.code == "DHL"
    assert result.name == "DHL Express"
    assert result.status == CarrierStatus.ACTIVE

    assert uow.carriers.items == [result]

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_create_carrier_rejects_duplicate_code_for_same_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    existing_carrier = Carrier(
        tenant_id=tenant_id,
        code="DHL",
        name="DHL",
        status=CarrierStatus.ACTIVE,
    )

    uow.carriers.items.append(existing_carrier)

    with pytest.raises(CarrierCodeAlreadyExistsError):
        await CreateCarrier(uow).execute(
            CreateCarrierCommand(
                tenant_id=tenant_id,
                code="  dhl  ",
                name="Another DHL",
            )
        )

    assert len(uow.carriers.items) == 1
    assert uow.flushed is False
    assert uow.committed is False
    assert uow.refreshed is False
    assert uow.rolled_back is True


async def test_create_carrier_allows_same_code_for_different_tenants() -> None:
    uow = FakeUnitOfWork()

    first_tenant_id = uuid4()
    second_tenant_id = uuid4()

    uow.carriers.items.append(
        Carrier(
            tenant_id=first_tenant_id,
            code="DHL",
            name="DHL",
            status=CarrierStatus.ACTIVE,
        )
    )

    result = await CreateCarrier(uow).execute(
        CreateCarrierCommand(
            tenant_id=second_tenant_id,
            code="DHL",
            name="DHL Second Tenant",
        )
    )

    assert result.tenant_id == second_tenant_id
    assert result.code == "DHL"

    assert len(uow.carriers.items) == 2

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False
