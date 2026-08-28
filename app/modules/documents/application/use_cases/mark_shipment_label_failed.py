from dataclasses import dataclass
from uuid import UUID

from app.modules.documents.application.exceptions import (
    InvalidShipmentLabelStateTransitionError,
    ShipmentLabelAlreadyVoidedError,
    ShipmentLabelNotFoundError,
)
from app.modules.documents.application.ports.unit_of_work import (
    DocumentsUnitOfWork,
)
from app.modules.documents.domain.enums import LabelStatus
from app.modules.documents.infrastructure.models.shipment_label import ShipmentLabel


@dataclass(frozen=True, slots=True)
class MarkShipmentLabelFailedCommand:
    tenant_id: UUID
    shipment_label_id: UUID


class MarkShipmentLabelFailedUseCase:
    def __init__(
        self,
        unit_of_work: DocumentsUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: MarkShipmentLabelFailedCommand,
    ) -> ShipmentLabel:
        async with self._unit_of_work:
            shipment_label = await self._unit_of_work.shipment_labels.get_by_id_and_tenant(
                command.shipment_label_id,
                command.tenant_id,
            )

            if shipment_label is None:
                raise ShipmentLabelNotFoundError

            if shipment_label.status == LabelStatus.VOIDED:
                raise ShipmentLabelAlreadyVoidedError

            if shipment_label.status != LabelStatus.PENDING:
                raise InvalidShipmentLabelStateTransitionError

            shipment_label.status = LabelStatus.FAILED

            await self._unit_of_work.flush()
            await self._unit_of_work.refresh(shipment_label)
            await self._unit_of_work.commit()

            return shipment_label
