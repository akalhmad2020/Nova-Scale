from dataclasses import dataclass
from uuid import UUID

from app.modules.carriers.application.exceptions import (
    CarrierServiceNotFoundError,
)
from app.modules.carriers.application.ports.unit_of_work import UnitOfWork
from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)


@dataclass(frozen=True, slots=True)
class GetCarrierServiceQuery:
    tenant_id: UUID
    carrier_service_id: UUID


class GetCarrierService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetCarrierServiceQuery,
    ) -> CarrierService:
        async with self._unit_of_work as uow:
            carrier_service = await uow.carrier_services.get_by_id_and_tenant(
                query.carrier_service_id,
                query.tenant_id,
            )

            if carrier_service is None:
                raise CarrierServiceNotFoundError

            return carrier_service
