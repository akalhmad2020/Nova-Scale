from dataclasses import dataclass
from uuid import UUID

from app.modules.carriers.application.exceptions import (
    CarrierServiceCodeAlreadyExistsError,
    CarrierServiceNotFoundError,
)
from app.modules.carriers.application.ports.unit_of_work import UnitOfWork
from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)
from app.modules.shipments.domain.enums import ServiceType


@dataclass(frozen=True, slots=True)
class UpdateCarrierServiceCommand:
    tenant_id: UUID
    carrier_service_id: UUID
    code: str | None = None
    name: str | None = None
    service_type: ServiceType | None = None


class UpdateCarrierService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: UpdateCarrierServiceCommand,
    ) -> CarrierService:
        async with self._unit_of_work as uow:
            carrier_service = await uow.carrier_services.get_by_id_and_tenant(
                command.carrier_service_id,
                command.tenant_id,
            )

            if carrier_service is None:
                raise CarrierServiceNotFoundError

            if command.code is not None:
                code = command.code.strip().upper()

                if code != carrier_service.code:
                    existing_service = await uow.carrier_services.get_by_code_and_carrier(
                        tenant_id=command.tenant_id,
                        carrier_id=carrier_service.carrier_id,
                        code=code,
                    )

                    if existing_service is not None:
                        raise CarrierServiceCodeAlreadyExistsError

                    carrier_service.code = code

            if command.name is not None:
                carrier_service.name = command.name.strip()

            if command.service_type is not None:
                carrier_service.service_type = command.service_type

            await uow.flush()
            await uow.commit()
            await uow.refresh(carrier_service)

            return carrier_service
