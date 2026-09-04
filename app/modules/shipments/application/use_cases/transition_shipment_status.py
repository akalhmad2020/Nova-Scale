from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.audit.application.contracts import AuditRecord
from app.modules.audit.application.use_cases.record_audit_log import (
    RecordAuditLogUseCase,
)
from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.shipment_events.domain.enums import ShipmentEventType
from app.modules.shipment_events.infrastructure.models.shipment_event import (
    ShipmentEvent,
)
from app.modules.shipments.application.exceptions import (
    InvalidShipmentStatusTransitionError,
    ShipmentNotFoundError,
)
from app.modules.shipments.application.ports.unit_of_work import UnitOfWork
from app.modules.shipments.domain.enums import ShipmentStatus
from app.modules.shipments.domain.lifecycle import (
    can_transition_shipment_status,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment


@dataclass(frozen=True, slots=True)
class TransitionShipmentStatusCommand:
    tenant_id: UUID
    actor_id: UUID
    shipment_id: UUID
    target_status: ShipmentStatus


class TransitionShipmentStatus:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: TransitionShipmentStatusCommand,
    ) -> Shipment:
        async with self._unit_of_work as uow:
            shipment = await uow.shipments.get_by_id_and_tenant(
                command.shipment_id,
                command.tenant_id,
            )

            if shipment is None:
                raise ShipmentNotFoundError

            previous_status = ShipmentStatus(
                shipment.status,
            )

            if not can_transition_shipment_status(
                previous_status,
                command.target_status,
            ):
                raise InvalidShipmentStatusTransitionError

            occurred_at = datetime.now(UTC)

            shipment.status = command.target_status

            shipment_event = ShipmentEvent(
                tenant_id=command.tenant_id,
                shipment_id=shipment.id,
                event_type=ShipmentEventType.STATUS_CHANGED,
                status=command.target_status,
                location_id=None,
                description=(
                    f"Shipment status changed from "
                    f"{previous_status.value} to "
                    f"{command.target_status.value}"
                ),
                occurred_at=occurred_at,
                metadata_={
                    "previous_status": previous_status.value,
                    "new_status": command.target_status.value,
                },
                created_by_user_id=command.actor_id,
            )

            uow.shipment_events.add(
                shipment_event,
            )

            await uow.flush()

            audit = RecordAuditLogUseCase(
                audit_logs=uow.audit_logs,
            )

            await audit.execute(
                AuditRecord(
                    tenant_id=command.tenant_id,
                    actor_type=AuditActorType.USER,
                    actor_id=command.actor_id,
                    action="shipment.status_changed",
                    resource_type="shipment",
                    resource_id=shipment.id,
                    outcome=AuditOutcome.SUCCESS,
                    metadata={
                        "tracking_number": shipment.tracking_number,
                        "previous_status": previous_status.value,
                        "new_status": command.target_status.value,
                    },
                    occurred_at=occurred_at,
                )
            )

            await uow.commit()
            await uow.refresh(shipment)

            return shipment
