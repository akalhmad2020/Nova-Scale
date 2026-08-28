from dataclasses import dataclass
from uuid import UUID

from app.modules.carriers.application.exceptions import (
    CarrierCodeAlreadyExistsError,
    CarrierNotFoundError,
)
from app.modules.carriers.application.ports.unit_of_work import UnitOfWork
from app.modules.carriers.infrastructure.models.carrier import Carrier


@dataclass(frozen=True, slots=True)
class UpdateCarrierCommand:
    tenant_id: UUID
    carrier_id: UUID
    code: str | None = None
    name: str | None = None


class UpdateCarrier:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: UpdateCarrierCommand,
    ) -> Carrier:
        async with self._unit_of_work as uow:
            carrier = await uow.carriers.get_by_id_and_tenant(
                command.carrier_id,
                command.tenant_id,
            )

            if carrier is None:
                raise CarrierNotFoundError

            if command.code is not None:
                code = command.code.strip().upper()

                if code != carrier.code:
                    existing_carrier = await uow.carriers.get_by_code_and_tenant(
                        code,
                        command.tenant_id,
                    )

                    if existing_carrier is not None:
                        raise CarrierCodeAlreadyExistsError

                    carrier.code = code

            if command.name is not None:
                carrier.name = command.name.strip()

            await uow.flush()
            await uow.commit()
            await uow.refresh(carrier)

            return carrier
