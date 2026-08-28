from dataclasses import dataclass
from uuid import UUID

from app.modules.carriers.application.exceptions import CarrierNotFoundError
from app.modules.carriers.application.ports.unit_of_work import UnitOfWork
from app.modules.carriers.infrastructure.models.carrier import Carrier


@dataclass(frozen=True, slots=True)
class GetCarrierQuery:
    tenant_id: UUID
    carrier_id: UUID


class GetCarrier:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetCarrierQuery,
    ) -> Carrier:
        async with self._unit_of_work as uow:
            carrier = await uow.carriers.get_by_id_and_tenant(
                query.carrier_id,
                query.tenant_id,
            )

            if carrier is None:
                raise CarrierNotFoundError

            return carrier
