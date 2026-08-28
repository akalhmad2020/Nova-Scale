from uuid import uuid4

import pytest

from app.modules.carriers.application.exceptions import (
    CarrierServiceAlreadyInactiveError,
    CarrierServiceNotFoundError,
)
from app.modules.carriers.application.use_cases.deactivate_carrier_service import (
    DeactivateCarrierService,
    DeactivateCarrierServiceCommand,
)
from app.modules.carriers.domain.enums import CarrierServiceStatus
from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)
from app.modules.shipments.domain.enums import ServiceType
from tests.unit.carriers.fakes import FakeUnitOfWork


async def test_deactivate_carrier_service_deactivates_active_service() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    carrier_service = CarrierService(
        id=uuid4(),
        tenant_id=tenant_id,
        carrier_id=uuid4(),
        code="EXPRESS",
        name="Express",
        service_type=ServiceType.EXPRESS,
        status=CarrierServiceStatus.ACTIVE,
    )

    uow.carrier_services.items.append(carrier_service)

    result = await DeactivateCarrierService(uow).execute(
        DeactivateCarrierServiceCommand(
            tenant_id=tenant_id,
            carrier_service_id=carrier_service.id,
        )
    )

    assert result.status == CarrierServiceStatus.INACTIVE

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_deactivate_carrier_service_rejects_already_inactive_service() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    carrier_service = CarrierService(
        id=uuid4(),
        tenant_id=tenant_id,
        carrier_id=uuid4(),
        code="EXPRESS",
        name="Express",
        service_type=ServiceType.EXPRESS,
        status=CarrierServiceStatus.INACTIVE,
    )

    uow.carrier_services.items.append(carrier_service)

    with pytest.raises(CarrierServiceAlreadyInactiveError):
        await DeactivateCarrierService(uow).execute(
            DeactivateCarrierServiceCommand(
                tenant_id=tenant_id,
                carrier_service_id=carrier_service.id,
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_deactivate_carrier_service_rejects_unknown_service() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(CarrierServiceNotFoundError):
        await DeactivateCarrierService(uow).execute(
            DeactivateCarrierServiceCommand(
                tenant_id=uuid4(),
                carrier_service_id=uuid4(),
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_deactivate_carrier_service_enforces_tenant_isolation() -> None:
    uow = FakeUnitOfWork()

    carrier_service = CarrierService(
        id=uuid4(),
        tenant_id=uuid4(),
        carrier_id=uuid4(),
        code="EXPRESS",
        name="Express",
        service_type=ServiceType.EXPRESS,
        status=CarrierServiceStatus.ACTIVE,
    )

    uow.carrier_services.items.append(carrier_service)

    with pytest.raises(CarrierServiceNotFoundError):
        await DeactivateCarrierService(uow).execute(
            DeactivateCarrierServiceCommand(
                tenant_id=uuid4(),
                carrier_service_id=carrier_service.id,
            )
        )

    assert carrier_service.status == CarrierServiceStatus.ACTIVE
    assert uow.committed is False
    assert uow.rolled_back is True
