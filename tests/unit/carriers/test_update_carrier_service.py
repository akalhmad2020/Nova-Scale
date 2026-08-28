from uuid import uuid4

import pytest

from app.modules.carriers.application.exceptions import (
    CarrierServiceCodeAlreadyExistsError,
    CarrierServiceNotFoundError,
)
from app.modules.carriers.application.use_cases.update_carrier_service import (
    UpdateCarrierService,
    UpdateCarrierServiceCommand,
)
from app.modules.carriers.domain.enums import CarrierServiceStatus
from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)
from app.modules.shipments.domain.enums import ServiceType
from tests.unit.carriers.fakes import FakeUnitOfWork


async def test_update_carrier_service_updates_fields() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    carrier_id = uuid4()

    carrier_service = CarrierService(
        id=uuid4(),
        tenant_id=tenant_id,
        carrier_id=carrier_id,
        code="STANDARD",
        name="Standard",
        service_type=ServiceType.STANDARD,
        status=CarrierServiceStatus.ACTIVE,
    )

    uow.carrier_services.items.append(carrier_service)

    result = await UpdateCarrierService(uow).execute(
        UpdateCarrierServiceCommand(
            tenant_id=tenant_id,
            carrier_service_id=carrier_service.id,
            code=" express ",
            name="  Express Delivery  ",
            service_type=ServiceType.EXPRESS,
        )
    )

    assert result is carrier_service
    assert result.code == "EXPRESS"
    assert result.name == "Express Delivery"
    assert result.service_type == ServiceType.EXPRESS

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_update_carrier_service_rejects_duplicate_code() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    carrier_id = uuid4()

    carrier_service = CarrierService(
        id=uuid4(),
        tenant_id=tenant_id,
        carrier_id=carrier_id,
        code="STANDARD",
        name="Standard",
        service_type=ServiceType.STANDARD,
        status=CarrierServiceStatus.ACTIVE,
    )

    existing_service = CarrierService(
        id=uuid4(),
        tenant_id=tenant_id,
        carrier_id=carrier_id,
        code="EXPRESS",
        name="Express",
        service_type=ServiceType.EXPRESS,
        status=CarrierServiceStatus.ACTIVE,
    )

    uow.carrier_services.items.extend(
        [
            carrier_service,
            existing_service,
        ]
    )

    with pytest.raises(CarrierServiceCodeAlreadyExistsError):
        await UpdateCarrierService(uow).execute(
            UpdateCarrierServiceCommand(
                tenant_id=tenant_id,
                carrier_service_id=carrier_service.id,
                code=" express ",
            )
        )

    assert carrier_service.code == "STANDARD"
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_update_carrier_service_allows_same_code_on_other_carrier() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()

    carrier_service = CarrierService(
        id=uuid4(),
        tenant_id=tenant_id,
        carrier_id=uuid4(),
        code="STANDARD",
        name="Standard",
        service_type=ServiceType.STANDARD,
        status=CarrierServiceStatus.ACTIVE,
    )

    uow.carrier_services.items.append(carrier_service)

    uow.carrier_services.items.append(
        CarrierService(
            id=uuid4(),
            tenant_id=tenant_id,
            carrier_id=uuid4(),
            code="EXPRESS",
            name="Other Express",
            service_type=ServiceType.EXPRESS,
            status=CarrierServiceStatus.ACTIVE,
        )
    )

    result = await UpdateCarrierService(uow).execute(
        UpdateCarrierServiceCommand(
            tenant_id=tenant_id,
            carrier_service_id=carrier_service.id,
            code="EXPRESS",
        )
    )

    assert result.code == "EXPRESS"
    assert uow.committed is True


async def test_update_carrier_service_rejects_foreign_tenant_service() -> None:
    uow = FakeUnitOfWork()

    carrier_service = CarrierService(
        id=uuid4(),
        tenant_id=uuid4(),
        carrier_id=uuid4(),
        code="STANDARD",
        name="Standard",
        service_type=ServiceType.STANDARD,
        status=CarrierServiceStatus.ACTIVE,
    )

    uow.carrier_services.items.append(carrier_service)

    with pytest.raises(CarrierServiceNotFoundError):
        await UpdateCarrierService(uow).execute(
            UpdateCarrierServiceCommand(
                tenant_id=uuid4(),
                carrier_service_id=carrier_service.id,
                name="Changed",
            )
        )

    assert carrier_service.name == "Standard"
    assert uow.committed is False
    assert uow.rolled_back is True
