from dataclasses import dataclass
from uuid import UUID

from app.modules.shipments.application.ports.unit_of_work import UnitOfWork
from app.modules.shipments.infrastructure.models.shipment import Shipment


@dataclass(frozen=True, slots=True)
class ListShipmentsQuery:
    tenant_id: UUID


class ListShipments:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: ListShipmentsQuery,
    ) -> list[Shipment]:
        async with self._unit_of_work as uow:
            return await uow.shipments.list_by_tenant(
                query.tenant_id,
            )
