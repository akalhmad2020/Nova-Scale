from uuid import uuid4

import pytest

from app.modules.carriers.application.exceptions import CarrierNotFoundError
from app.modules.carriers.application.use_cases.list_carrier_services import (
    ListCarrierServices,
    ListCarrierServicesQuery,
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


async def test_list_carrier_services_returns_services_for_carrier() -> None:
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

    first_service = CarrierService(
        tenant_id=tenant_id,
        carrier_id=carrier_id,
        code="EXPRESS",
        name="Express",
        service_type=ServiceType.EXPRESS,
        status=CarrierServiceStatus.ACTIVE,
    )

    second_service = CarrierService(
        tenant_id=tenant_id,
        carrier_id=carrier_id,
        code="STANDARD",
        name="Standard",
        service_type=ServiceType.STANDARD,
        status=CarrierServiceStatus.ACTIVE,
    )

    uow.carrier_services.items.extend(
        [
            first_service,
            second_service,
        ]
    )

    result = await ListCarrierServices(uow).execute(
        ListCarrierServicesQuery(
            tenant_id=tenant_id,
            carrier_id=carrier_id,
        )
    )

    assert result == [
        first_service,
        second_service,
    ]


async def test_list_carrier_services_returns_empty_list_for_carrier() -> None:
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

    result = await ListCarrierServices(uow).execute(
        ListCarrierServicesQuery(
            tenant_id=tenant_id,
            carrier_id=carrier_id,
        )
    )

    assert result == []


async def test_list_carrier_services_excludes_other_carriers() -> None:
    uow = FakeUnitOfWork()

    tenant_id = uuid4()
    carrier_id = uuid4()
    other_carrier_id = uuid4()

    uow.carriers.items.append(
        Carrier(
            id=carrier_id,
            tenant_id=tenant_id,
            code="DHL",
            name="DHL",
            status=CarrierStatus.ACTIVE,
        )
    )

    expected_service = CarrierService(
        tenant_id=tenant_id,
        carrier_id=carrier_id,
        code="EXPRESS",
        name="Express",
        service_type=ServiceType.EXPRESS,
        status=CarrierServiceStatus.ACTIVE,
    )

    other_service = CarrierService(
        tenant_id=tenant_id,
        carrier_id=other_carrier_id,
        code="EXPRESS",
        name="Other Express",
        service_type=ServiceType.EXPRESS,
        status=CarrierServiceStatus.ACTIVE,
    )

    uow.carrier_services.items.extend(
        [
            expected_service,
            other_service,
        ]
    )

    result = await ListCarrierServices(uow).execute(
        ListCarrierServicesQuery(
            tenant_id=tenant_id,
            carrier_id=carrier_id,
        )
    )

    assert result == [expected_service]


async def test_list_carrier_services_rejects_unknown_carrier() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(CarrierNotFoundError):
        await ListCarrierServices(uow).execute(
            ListCarrierServicesQuery(
                tenant_id=uuid4(),
                carrier_id=uuid4(),
            )
        )


async def test_list_carrier_services_enforces_tenant_isolation() -> None:
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
        await ListCarrierServices(uow).execute(
            ListCarrierServicesQuery(
                tenant_id=uuid4(),
                carrier_id=carrier_id,
            )
        )
