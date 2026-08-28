from uuid import uuid4

import pytest

from app.modules.carriers.application.exceptions import (
    CarrierInactiveError,
    CarrierNotFoundError,
    CarrierServiceCodeAlreadyExistsError,
)
from app.modules.carriers.application.use_cases.create_carrier_service import (
    CreateCarrierService,
    CreateCarrierServiceCommand,
)
from app.modules.carriers.domain.enums import (
    CarrierServiceStatus,
    CarrierStatus,
)
from app.modules.carriers.infrastructure.models.carrier import Carrier
from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)
from app.modules.shipments.domain.enums import ServiceType
from tests.unit.carriers.fakes import FakeUnitOfWork


async def test_create_carrier_service_creates_active_service() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    carrier_id = uuid4()

    uow.carriers.items.append(
        Carrier(
            id=carrier_id,
            tenant_id=tenant_id,
            code="DHL",
            name="DHL",
            status=CarrierStatus.ACTIVE,
        )
    )

    result = await CreateCarrierService(uow).execute(
        CreateCarrierServiceCommand(
            tenant_id=tenant_id,
            carrier_id=carrier_id,
            code="  express  ",
            name="  DHL Express  ",
            service_type=ServiceType.EXPRESS,
        )
    )

    assert result.tenant_id == tenant_id
    assert result.carrier_id == carrier_id
    assert result.code == "EXPRESS"
    assert result.name == "DHL Express"
    assert result.service_type == ServiceType.EXPRESS
    assert result.status == CarrierServiceStatus.ACTIVE

    assert uow.carrier_services.items == [result]

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.refreshed is True
    assert uow.rolled_back is False


async def test_create_carrier_service_rejects_unknown_carrier() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(CarrierNotFoundError):
        await CreateCarrierService(uow).execute(
            CreateCarrierServiceCommand(
                tenant_id=uuid4(),
                carrier_id=uuid4(),
                code="EXPRESS",
                name="Express",
                service_type=ServiceType.EXPRESS,
            )
        )

    assert uow.carrier_services.items == []
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_carrier_service_rejects_foreign_tenant_carrier() -> None:
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
        await CreateCarrierService(uow).execute(
            CreateCarrierServiceCommand(
                tenant_id=uuid4(),
                carrier_id=carrier_id,
                code="EXPRESS",
                name="Express",
                service_type=ServiceType.EXPRESS,
            )
        )

    assert uow.carrier_services.items == []
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_carrier_service_rejects_inactive_carrier() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    carrier_id = uuid4()

    uow.carriers.items.append(
        Carrier(
            id=carrier_id,
            tenant_id=tenant_id,
            code="DHL",
            name="DHL",
            status=CarrierStatus.INACTIVE,
        )
    )

    with pytest.raises(CarrierInactiveError):
        await CreateCarrierService(uow).execute(
            CreateCarrierServiceCommand(
                tenant_id=tenant_id,
                carrier_id=carrier_id,
                code="EXPRESS",
                name="Express",
                service_type=ServiceType.EXPRESS,
            )
        )

    assert uow.carrier_services.items == []
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_carrier_service_rejects_duplicate_code_for_same_carrier() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    carrier_id = uuid4()

    uow.carriers.items.append(
        Carrier(
            id=carrier_id,
            tenant_id=tenant_id,
            code="DHL",
            name="DHL",
            status=CarrierStatus.ACTIVE,
        )
    )

    uow.carrier_services.items.append(
        CarrierService(
            tenant_id=tenant_id,
            carrier_id=carrier_id,
            code="EXPRESS",
            name="Existing Express",
            service_type=ServiceType.EXPRESS,
            status=CarrierServiceStatus.ACTIVE,
        )
    )

    with pytest.raises(CarrierServiceCodeAlreadyExistsError):
        await CreateCarrierService(uow).execute(
            CreateCarrierServiceCommand(
                tenant_id=tenant_id,
                carrier_id=carrier_id,
                code="  express  ",
                name="Another Express",
                service_type=ServiceType.EXPRESS,
            )
        )

    assert len(uow.carrier_services.items) == 1
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_create_carrier_service_allows_same_code_for_different_carriers() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    first_carrier_id = uuid4()
    second_carrier_id = uuid4()

    uow.carriers.items.extend(
        [
            Carrier(
                id=first_carrier_id,
                tenant_id=tenant_id,
                code="DHL",
                name="DHL",
                status=CarrierStatus.ACTIVE,
            ),
            Carrier(
                id=second_carrier_id,
                tenant_id=tenant_id,
                code="ARAMEX",
                name="Aramex",
                status=CarrierStatus.ACTIVE,
            ),
        ]
    )

    uow.carrier_services.items.append(
        CarrierService(
            tenant_id=tenant_id,
            carrier_id=first_carrier_id,
            code="EXPRESS",
            name="DHL Express",
            service_type=ServiceType.EXPRESS,
            status=CarrierServiceStatus.ACTIVE,
        )
    )

    result = await CreateCarrierService(uow).execute(
        CreateCarrierServiceCommand(
            tenant_id=tenant_id,
            carrier_id=second_carrier_id,
            code="EXPRESS",
            name="Aramex Express",
            service_type=ServiceType.EXPRESS,
        )
    )

    assert result.carrier_id == second_carrier_id
    assert result.code == "EXPRESS"
    assert len(uow.carrier_services.items) == 2
    assert uow.committed is True
