from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.audit.application.contracts import AuditRecord
from app.modules.audit.application.use_cases.record_audit_log import (
    RecordAuditLogUseCase,
)
from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.shipments.application.exceptions import ShipmentNotFoundError
from app.modules.shipments.application.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class DeleteShipmentCommand:
    tenant_id: UUID
    actor_id: UUID
    shipment_id: UUID


class DeleteShipment:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: DeleteShipmentCommand,
    ) -> None:
        async with self._unit_of_work as uow:
            shipment = await uow.shipments.get_by_id_and_tenant(
                command.shipment_id,
                command.tenant_id,
            )

            if shipment is None:
                raise ShipmentNotFoundError

            deleted_at = datetime.now(UTC)

            shipment.deleted_at = deleted_at

            await uow.flush()

            audit = RecordAuditLogUseCase(
                audit_logs=uow.audit_logs,
            )

            await audit.execute(
                AuditRecord(
                    tenant_id=command.tenant_id,
                    actor_type=AuditActorType.USER,
                    actor_id=command.actor_id,
                    action="shipment.deleted",
                    resource_type="shipment",
                    resource_id=shipment.id,
                    outcome=AuditOutcome.SUCCESS,
                    metadata={
                        "tracking_number": shipment.tracking_number,
                        "customer_id": str(shipment.customer_id),
                        "origin_location_id": str(shipment.origin_location_id),
                        "destination_location_id": str(shipment.destination_location_id),
                        "status": shipment.status.value,
                        "service_type": shipment.service_type.value,
                        "weight": str(shipment.weight),
                        "weight_unit": shipment.weight_unit.value,
                        "deleted_at": deleted_at.isoformat(),
                    },
                    occurred_at=deleted_at,
                )
            )

            await uow.commit()
