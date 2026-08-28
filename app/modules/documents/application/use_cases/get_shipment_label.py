from dataclasses import dataclass
from uuid import UUID

from app.modules.documents.application.exceptions import (
    ShipmentLabelNotFoundError,
)
from app.modules.documents.application.ports.unit_of_work import (
    DocumentsUnitOfWork,
)
from app.modules.documents.infrastructure.models.shipment_label import ShipmentLabel


@dataclass(frozen=True, slots=True)
class GetShipmentLabelQuery:
    tenant_id: UUID
    shipment_label_id: UUID


class GetShipmentLabelUseCase:
    def __init__(
        self,
        unit_of_work: DocumentsUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetShipmentLabelQuery,
    ) -> ShipmentLabel:
        async with self._unit_of_work:
            shipment_label = await self._unit_of_work.shipment_labels.get_by_id_and_tenant(
                query.shipment_label_id,
                query.tenant_id,
            )

            if shipment_label is None:
                raise ShipmentLabelNotFoundError

            return shipment_label
