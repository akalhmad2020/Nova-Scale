from dataclasses import dataclass
from uuid import UUID

from app.modules.shipments.application.exceptions import ShipmentNotFoundError
from app.modules.shipments.application.ports.unit_of_work import UnitOfWork
from app.modules.shipments.infrastructure.models.shipment import Shipment


@dataclass(frozen=True, slots=True)
class GetShipmentQuery:
    tenant_id: UUID
    shipment_id: UUID


class GetShipment:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetShipmentQuery,
    ) -> Shipment:
        async with self._unit_of_work as uow:
            shipment = await uow.shipments.get_by_id_and_tenant(
                query.shipment_id,
                query.tenant_id,
            )

            if shipment is None:
                raise ShipmentNotFoundError

            return shipment
