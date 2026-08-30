from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.audit.application.contracts import AuditRecord
from app.modules.audit.application.use_cases.record_audit_log import (
    RecordAuditLogUseCase,
)
from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.shipments.application.exceptions import (
    ShipmentCustomerNotFoundError,
    ShipmentDestinationLocationNotFoundError,
    ShipmentOriginLocationNotFoundError,
    ShipmentTrackingNumberAlreadyExistsError,
)
from app.modules.shipments.application.ports.unit_of_work import UnitOfWork
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment


@dataclass(frozen=True, slots=True)
class CreateShipmentCommand:
    tenant_id: UUID
    actor_id: UUID
    customer_id: UUID
    origin_location_id: UUID
    destination_location_id: UUID
    tracking_number: str
    service_type: ServiceType
    weight: Decimal
    weight_unit: WeightUnit
    reference: str | None = None
    description: str | None = None
    notes: str | None = None


class CreateShipment:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateShipmentCommand,
    ) -> Shipment:
        tracking_number = command.tracking_number.strip().upper()

        reference = command.reference.strip() if command.reference is not None else None

        description = command.description.strip() if command.description is not None else None

        notes = command.notes.strip() if command.notes is not None else None

        async with self._unit_of_work as uow:
            existing = await uow.shipments.get_by_tracking_number_and_tenant(
                tracking_number,
                command.tenant_id,
            )

            if existing is not None:
                raise ShipmentTrackingNumberAlreadyExistsError

            customer = await uow.customers.get_by_id_and_tenant(
                command.customer_id,
                command.tenant_id,
            )

            if customer is None:
                raise ShipmentCustomerNotFoundError

            origin = await uow.locations.get_by_id_and_tenant(
                command.origin_location_id,
                command.tenant_id,
            )

            if origin is None:
                raise ShipmentOriginLocationNotFoundError

            destination = await uow.locations.get_by_id_and_tenant(
                command.destination_location_id,
                command.tenant_id,
            )

            if destination is None:
                raise ShipmentDestinationLocationNotFoundError

            shipment = Shipment(
                tenant_id=command.tenant_id,
                customer_id=command.customer_id,
                origin_location_id=command.origin_location_id,
                destination_location_id=command.destination_location_id,
                tracking_number=tracking_number,
                reference=reference,
                status=ShipmentStatus.DRAFT,
                service_type=command.service_type,
                description=description,
                weight=command.weight,
                weight_unit=command.weight_unit,
                notes=notes,
            )

            uow.shipments.add(shipment)

            await uow.flush()

            audit = RecordAuditLogUseCase(
                audit_logs=uow.audit_logs,
            )

            await audit.execute(
                AuditRecord(
                    tenant_id=command.tenant_id,
                    actor_type=AuditActorType.USER,
                    actor_id=command.actor_id,
                    action="shipment.created",
                    resource_type="shipment",
                    resource_id=shipment.id,
                    outcome=AuditOutcome.SUCCESS,
                    metadata={
                        "tracking_number": shipment.tracking_number,
                        "customer_id": str(shipment.customer_id),
                        "origin_location_id": str(shipment.origin_location_id),
                        "destination_location_id": str(shipment.destination_location_id),
                        "service_type": command.service_type.value,
                        "weight": str(command.weight),
                        "weight_unit": command.weight_unit.value,
                    },
                )
            )

            await uow.commit()
            await uow.refresh(shipment)

            return shipment
