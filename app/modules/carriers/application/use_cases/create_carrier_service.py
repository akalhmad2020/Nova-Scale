from dataclasses import dataclass
from uuid import UUID

from app.modules.carriers.application.exceptions import (
    CarrierInactiveError,
    CarrierNotFoundError,
    CarrierServiceCodeAlreadyExistsError,
)
from app.modules.carriers.application.ports.unit_of_work import UnitOfWork
from app.modules.carriers.domain.enums import (
    CarrierServiceStatus,
    CarrierStatus,
)
from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)
from app.modules.shipments.domain.enums import ServiceType


@dataclass(frozen=True, slots=True)
class CreateCarrierServiceCommand:
    tenant_id: UUID
    carrier_id: UUID
    code: str
    name: str
    service_type: ServiceType


class CreateCarrierService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateCarrierServiceCommand,
    ) -> CarrierService:
        code = command.code.strip().upper()
        name = command.name.strip()

        async with self._unit_of_work as uow:
            carrier = await uow.carriers.get_by_id_and_tenant(
                command.carrier_id,
                command.tenant_id,
            )

            if carrier is None:
                raise CarrierNotFoundError

            if carrier.status == CarrierStatus.INACTIVE:
                raise CarrierInactiveError

            existing_service = await uow.carrier_services.get_by_code_and_carrier(
                tenant_id=command.tenant_id,
                carrier_id=command.carrier_id,
                code=code,
            )

            if existing_service is not None:
                raise CarrierServiceCodeAlreadyExistsError

            carrier_service = CarrierService(
                tenant_id=command.tenant_id,
                carrier_id=command.carrier_id,
                code=code,
                name=name,
                service_type=command.service_type,
                status=CarrierServiceStatus.ACTIVE,
            )

            uow.carrier_services.add(carrier_service)

            await uow.flush()
            await uow.commit()
            await uow.refresh(carrier_service)

            return carrier_service
