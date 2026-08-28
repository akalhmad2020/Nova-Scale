from uuid import uuid4

import pytest

from app.modules.carriers.application.exceptions import CarrierNotFoundError
from app.modules.carriers.application.use_cases.get_carrier import (
    GetCarrier,
    GetCarrierQuery,
)
from app.modules.carriers.domain.enums import CarrierStatus
from app.modules.carriers.infrastructure.models.carrier import Carrier
from tests.unit.carriers.fakes import FakeUnitOfWork


async def test_get_carrier_returns_carrier_for_tenant() -> None:
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

    result = await GetCarrier(uow).execute(
        GetCarrierQuery(
            tenant_id=tenant_id,
            carrier_id=carrier_id,
        )
    )

    assert result is carrier


async def test_get_carrier_rejects_unknown_carrier() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(CarrierNotFoundError):
        await GetCarrier(uow).execute(
            GetCarrierQuery(
                tenant_id=uuid4(),
                carrier_id=uuid4(),
            )
        )


async def test_get_carrier_enforces_tenant_isolation() -> None:
    uow = FakeUnitOfWork()

    carrier_id = uuid4()

    uow.carriers.items.append(
        Carrier(
            id=carrier_id,
            tenant_id=uuid4(),
            code="DHL",
            name="DHL",
            status=CarrierStatus.ACTIVE,
        )
    )

    with pytest.raises(CarrierNotFoundError):
        await GetCarrier(uow).execute(
            GetCarrierQuery(
                tenant_id=uuid4(),
                carrier_id=carrier_id,
            )
        )
