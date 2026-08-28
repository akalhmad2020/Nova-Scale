from dataclasses import dataclass
from uuid import UUID

from app.modules.carriers.application.exceptions import (
    CarrierServiceAlreadyInactiveError,
    CarrierServiceNotFoundError,
)
from app.modules.carriers.application.ports.unit_of_work import UnitOfWork
from app.modules.carriers.domain.enums import CarrierServiceStatus
from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)


@dataclass(frozen=True, slots=True)
class DeactivateCarrierServiceCommand:
    tenant_id: UUID
    carrier_service_id: UUID


class DeactivateCarrierService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: DeactivateCarrierServiceCommand,
    ) -> CarrierService:
        async with self._unit_of_work as uow:
            carrier_service = await uow.carrier_services.get_by_id_and_tenant(
                command.carrier_service_id,
                command.tenant_id,
            )

            if carrier_service is None:
                raise CarrierServiceNotFoundError

            if carrier_service.status == CarrierServiceStatus.INACTIVE:
                raise CarrierServiceAlreadyInactiveError

            carrier_service.status = CarrierServiceStatus.INACTIVE

            await uow.flush()
            await uow.commit()
            await uow.refresh(carrier_service)

            return carrier_service
