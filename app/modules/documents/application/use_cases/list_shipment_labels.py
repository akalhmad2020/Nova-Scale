from dataclasses import dataclass
from uuid import UUID

from app.modules.documents.application.ports.unit_of_work import (
    DocumentsUnitOfWork,
)
from app.modules.documents.infrastructure.models.shipment_label import ShipmentLabel


@dataclass(frozen=True, slots=True)
class ListShipmentLabelsQuery:
    tenant_id: UUID
    shipment_id: UUID


class ListShipmentLabelsUseCase:
    def __init__(
        self,
        unit_of_work: DocumentsUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: ListShipmentLabelsQuery,
    ) -> list[ShipmentLabel]:
        async with self._unit_of_work:
            return await self._unit_of_work.shipment_labels.list_by_shipment(
                query.shipment_id,
                query.tenant_id,
            )
