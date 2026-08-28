from uuid import uuid4

import pytest

from app.modules.carriers.application.exceptions import (
    CarrierServiceNotFoundError,
)
from app.modules.carriers.application.use_cases.get_carrier_service import (
    GetCarrierService,
    GetCarrierServiceQuery,
)
from app.modules.carriers.domain.enums import (
    CarrierServiceStatus,
)
from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)
from app.modules.shipments.domain.enums import ServiceType
from tests.unit.carriers.fakes import FakeUnitOfWork


async def test_get_carrier_service_returns_service_for_tenant() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    carrier_id = uuid4()
    carrier_service_id = uuid4()

    carrier_service = CarrierService(
        id=carrier_service_id,
        tenant_id=tenant_id,
        carrier_id=carrier_id,
        code="EXPRESS",
        name="Express",
        service_type=ServiceType.EXPRESS,
        status=CarrierServiceStatus.ACTIVE,
    )

    uow.carrier_services.items.append(carrier_service)

    result = await GetCarrierService(uow).execute(
        GetCarrierServiceQuery(
            tenant_id=tenant_id,
            carrier_service_id=carrier_service_id,
        )
    )

    assert result is carrier_service


async def test_get_carrier_service_rejects_unknown_service() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(CarrierServiceNotFoundError):
        await GetCarrierService(uow).execute(
            GetCarrierServiceQuery(
                tenant_id=uuid4(),
                carrier_service_id=uuid4(),
            )
        )


async def test_get_carrier_service_enforces_tenant_isolation() -> None:
    uow = FakeUnitOfWork()

    carrier_service_id = uuid4()

    uow.carrier_services.items.append(
        CarrierService(
            id=carrier_service_id,
            tenant_id=uuid4(),
            carrier_id=uuid4(),
            code="EXPRESS",
            name="Express",
            service_type=ServiceType.EXPRESS,
            status=CarrierServiceStatus.ACTIVE,
        )
    )

    with pytest.raises(CarrierServiceNotFoundError):
        await GetCarrierService(uow).execute(
            GetCarrierServiceQuery(
                tenant_id=uuid4(),
                carrier_service_id=carrier_service_id,
            )
        )
