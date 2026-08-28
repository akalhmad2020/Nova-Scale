from dataclasses import dataclass
from uuid import UUID

from app.modules.carriers.application.exceptions import (
    CarrierCodeAlreadyExistsError,
)
from app.modules.carriers.application.ports.unit_of_work import UnitOfWork
from app.modules.carriers.domain.enums import CarrierStatus
from app.modules.carriers.infrastructure.models.carrier import Carrier


@dataclass(frozen=True, slots=True)
class CreateCarrierCommand:
    tenant_id: UUID
    code: str
    name: str


class CreateCarrier:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateCarrierCommand,
    ) -> Carrier:
        code = command.code.strip().upper()
        name = command.name.strip()

        async with self._unit_of_work as uow:
            existing_carrier = await uow.carriers.get_by_code_and_tenant(
                code,
                command.tenant_id,
            )

            if existing_carrier is not None:
                raise CarrierCodeAlreadyExistsError

            carrier = Carrier(
                tenant_id=command.tenant_id,
                code=code,
                name=name,
                status=CarrierStatus.ACTIVE,
            )

            uow.carriers.add(carrier)

            await uow.flush()
            await uow.commit()
            await uow.refresh(carrier)

            return carrier
