from dataclasses import dataclass
from uuid import UUID

from app.modules.documents.application.events import (
    DOCUMENT_READY_EVENT_TYPE,
)
from app.modules.documents.application.exceptions import (
    DocumentNotFoundError,
    DocumentShipmentMismatchError,
    InvalidDocumentStateTransitionError,
    InvalidShipmentLabelStateTransitionError,
    InvalidShippingLabelDocumentError,
    ShipmentLabelAlreadyVoidedError,
    ShipmentLabelNotFoundError,
)
from app.modules.documents.application.ports.unit_of_work import (
    DocumentsUnitOfWork,
)
from app.modules.documents.domain.enums import (
    DocumentStatus,
    DocumentType,
    LabelStatus,
)
from app.modules.documents.infrastructure.models.shipment_label import ShipmentLabel
from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)


@dataclass(frozen=True, slots=True)
class CompleteShipmentLabelCommand:
    tenant_id: UUID
    shipment_label_id: UUID
    document_id: UUID
    tracking_number: str | None = None


class CompleteShipmentLabelUseCase:
    def __init__(
        self,
        unit_of_work: DocumentsUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CompleteShipmentLabelCommand,
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

            document = await self._unit_of_work.documents.get_by_id_and_tenant(
                command.document_id,
                command.tenant_id,
            )

            if document is None:
                raise DocumentNotFoundError

            if document.shipment_id != shipment_label.shipment_id:
                raise DocumentShipmentMismatchError

            if document.type != DocumentType.SHIPPING_LABEL:
                raise InvalidShippingLabelDocumentError

            if document.status != DocumentStatus.PENDING:
                raise InvalidDocumentStateTransitionError

            document.status = DocumentStatus.READY

            shipment_label.document_id = document.id
            shipment_label.status = LabelStatus.GENERATED

            if command.tracking_number is not None:
                shipment_label.tracking_number = command.tracking_number.strip()

            outbox_message = OutboxMessage(
                tenant_id=command.tenant_id,
                event_type=DOCUMENT_READY_EVENT_TYPE,
                payload={
                    "document_id": str(document.id),
                },
                status=OutboxMessageStatus.PENDING.value,
                attempt_count=0,
                available_at=None,
                claim_token=None,
                lease_expires_at=None,
                processed_at=None,
                last_error=None,
            )

            await self._unit_of_work.outbox_messages.add(
                outbox_message,
            )

            await self._unit_of_work.flush()
            await self._unit_of_work.refresh(shipment_label)
            await self._unit_of_work.commit()

            return shipment_label
