from uuid import uuid4

from app.modules.carriers.application.use_cases.list_carriers import (
    ListCarriers,
    ListCarriersQuery,
)
from app.modules.carriers.domain.enums import CarrierStatus
from app.modules.carriers.infrastructure.models.carrier import Carrier
from tests.unit.carriers.fakes import FakeUnitOfWork


async def test_list_carriers_returns_only_tenant_carriers() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    foreign_tenant_id = uuid4()

    first_carrier = Carrier(
        tenant_id=tenant_id,
        code="DHL",
        name="DHL",
        status=CarrierStatus.ACTIVE,
    )

    second_carrier = Carrier(
        tenant_id=tenant_id,
        code="ARAMEX",
        name="Aramex",
        status=CarrierStatus.ACTIVE,
    )

    foreign_carrier = Carrier(
        tenant_id=foreign_tenant_id,
        code="UPS",
        name="UPS",
        status=CarrierStatus.ACTIVE,
    )

    uow.carriers.items.extend(
        [
            first_carrier,
            second_carrier,
            foreign_carrier,
        ]
    )

    result = await ListCarriers(uow).execute(
        ListCarriersQuery(
            tenant_id=tenant_id,
        )
    )

    assert result == [
        first_carrier,
        second_carrier,
    ]


async def test_list_carriers_returns_empty_list() -> None:
    uow = FakeUnitOfWork()

    result = await ListCarriers(uow).execute(
        ListCarriersQuery(
            tenant_id=uuid4(),
        )
    )

    assert result == []
