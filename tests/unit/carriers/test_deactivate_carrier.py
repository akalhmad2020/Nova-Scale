from uuid import uuid4

import pytest

from app.modules.carriers.application.exceptions import (
    CarrierAlreadyInactiveError,
    CarrierNotFoundError,
)
from app.modules.carriers.application.use_cases.deactivate_carrier import (
    DeactivateCarrier,
    DeactivateCarrierCommand,
)
from app.modules.carriers.domain.enums import CarrierStatus
from app.modules.carriers.infrastructure.models.carrier import Carrier
from tests.unit.carriers.fakes import FakeUnitOfWork


async def test_deactivate_carrier_deactivates_active_carrier() -> None:
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

    result = await DeactivateCarrier(uow).execute(
        DeactivateCarrierCommand(
            tenant_id=tenant_id,
            carrier_id=carrier.id,
        )
    )

    assert result.status == CarrierStatus.INACTIVE

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_deactivate_carrier_rejects_already_inactive_carrier() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    carrier = Carrier(
        id=uuid4(),
        tenant_id=tenant_id,
        code="DHL",
        name="DHL",
        status=CarrierStatus.INACTIVE,
    )

    uow.carriers.items.append(carrier)

    with pytest.raises(CarrierAlreadyInactiveError):
        await DeactivateCarrier(uow).execute(
            DeactivateCarrierCommand(
                tenant_id=tenant_id,
                carrier_id=carrier.id,
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_deactivate_carrier_rejects_unknown_carrier() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(CarrierNotFoundError):
        await DeactivateCarrier(uow).execute(
            DeactivateCarrierCommand(
                tenant_id=uuid4(),
                carrier_id=uuid4(),
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_deactivate_carrier_enforces_tenant_isolation() -> None:
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
        await DeactivateCarrier(uow).execute(
            DeactivateCarrierCommand(
                tenant_id=uuid4(),
                carrier_id=carrier.id,
            )
        )

    assert carrier.status == CarrierStatus.ACTIVE
    assert uow.committed is False
    assert uow.rolled_back is True
