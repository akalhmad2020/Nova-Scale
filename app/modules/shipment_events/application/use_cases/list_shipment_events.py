from dataclasses import dataclass
from uuid import UUID

from app.modules.shipment_events.application.exceptions import (
    ShipmentEventShipmentNotFoundError,
)
from app.modules.shipment_events.application.ports.unit_of_work import UnitOfWork
from app.modules.shipment_events.infrastructure.models.shipment_event import (
    ShipmentEvent,
)


@dataclass(frozen=True, slots=True)
class ListShipmentEventsQuery:
    tenant_id: UUID
    shipment_id: UUID


class ListShipmentEvents:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: ListShipmentEventsQuery,
    ) -> list[ShipmentEvent]:
        async with self._unit_of_work as uow:
            shipment = await uow.shipments.get_by_id_and_tenant(
                query.shipment_id,
                query.tenant_id,
            )

            if shipment is None:
                raise ShipmentEventShipmentNotFoundError

            return await uow.shipment_events.list_by_shipment(
                query.shipment_id,
                query.tenant_id,
            )
