from dataclasses import dataclass
from uuid import UUID

from app.modules.carriers.application.exceptions import (
    CarrierAlreadyInactiveError,
    CarrierNotFoundError,
)
from app.modules.carriers.application.ports.unit_of_work import UnitOfWork
from app.modules.carriers.domain.enums import CarrierStatus
from app.modules.carriers.infrastructure.models.carrier import Carrier


@dataclass(frozen=True, slots=True)
class DeactivateCarrierCommand:
    tenant_id: UUID
    carrier_id: UUID


class DeactivateCarrier:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: DeactivateCarrierCommand,
    ) -> Carrier:
        async with self._unit_of_work as uow:
            carrier = await uow.carriers.get_by_id_and_tenant(
                command.carrier_id,
                command.tenant_id,
            )

            if carrier is None:
                raise CarrierNotFoundError

            if carrier.status == CarrierStatus.INACTIVE:
                raise CarrierAlreadyInactiveError

            carrier.status = CarrierStatus.INACTIVE

            await uow.flush()
            await uow.commit()
            await uow.refresh(carrier)

            return carrier
