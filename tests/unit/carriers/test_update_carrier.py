from uuid import uuid4

import pytest

from app.modules.carriers.application.exceptions import (
    CarrierCodeAlreadyExistsError,
    CarrierNotFoundError,
)
from app.modules.carriers.application.use_cases.update_carrier import (
    UpdateCarrier,
    UpdateCarrierCommand,
)
from app.modules.carriers.domain.enums import CarrierStatus
from app.modules.carriers.infrastructure.models.carrier import Carrier
from tests.unit.carriers.fakes import FakeUnitOfWork


async def test_update_carrier_updates_fields() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    carrier_id = uuid4()

    carrier = Carrier(
        id=carrier_id,
        tenant_id=tenant_id,
        code="DHL",
        name="DHL",
        status=CarrierStatus.ACTIVE,
    )

    uow.carriers.items.append(carrier)

    result = await UpdateCarrier(uow).execute(
        UpdateCarrierCommand(
            tenant_id=tenant_id,
            carrier_id=carrier_id,
            code="  aramex  ",
            name="  Aramex Express  ",
        )
    )

    assert result is carrier
    assert result.code == "ARAMEX"
    assert result.name == "Aramex Express"

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_update_carrier_rejects_duplicate_code() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    carrier = Carrier(
        id=uuid4(),
        tenant_id=tenant_id,
        code="DHL",
        name="DHL",
        status=CarrierStatus.ACTIVE,
    )

    existing_carrier = Carrier(
        id=uuid4(),
        tenant_id=tenant_id,
        code="ARAMEX",
        name="Aramex",
        status=CarrierStatus.ACTIVE,
    )

    uow.carriers.items.extend(
        [
            carrier,
            existing_carrier,
        ]
    )

    with pytest.raises(CarrierCodeAlreadyExistsError):
        await UpdateCarrier(uow).execute(
            UpdateCarrierCommand(
                tenant_id=tenant_id,
                carrier_id=carrier.id,
                code=" aramex ",
            )
        )

    assert carrier.code == "DHL"
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_carrier_allows_unchanged_code() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    carrier = Carrier(
        id=uuid4(),
        tenant_id=tenant_id,
        code="DHL",
        name="DHL",
        status=CarrierStatus.ACTIVE,
    )

    uow.carriers.items.append(carrier)

    result = await UpdateCarrier(uow).execute(
        UpdateCarrierCommand(
            tenant_id=tenant_id,
            carrier_id=carrier.id,
            code=" dhl ",
            name="DHL Express",
        )
    )

    assert result.code == "DHL"
    assert result.name == "DHL Express"
    assert uow.committed is True


async def test_update_carrier_rejects_foreign_tenant_carrier() -> None:
    uow = FakeUnitOfWork()

    carrier = Carrier(
        id=uuid4(),
        tenant_id=uuid4(),
        code="DHL",
        name="DHL",
        status=CarrierStatus.ACTIVE,
    )

    uow.carriers.items.append(carrier)

    with pytest.raises(CarrierNotFoundError):
        await UpdateCarrier(uow).execute(
            UpdateCarrierCommand(
                tenant_id=uuid4(),
                carrier_id=carrier.id,
                name="Changed",
            )
        )

    assert carrier.name == "DHL"
    assert uow.committed is False
    assert uow.rolled_back is True
