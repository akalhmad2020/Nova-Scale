from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.shipment_events.application.exceptions import (
    ShipmentEventLocationNotFoundError,
    ShipmentEventShipmentNotFoundError,
)
from app.modules.shipment_events.application.ports.unit_of_work import UnitOfWork
from app.modules.shipment_events.domain.enums import ShipmentEventType
from app.modules.shipment_events.infrastructure.models.shipment_event import (
    ShipmentEvent,
)
from app.modules.shipments.domain.enums import ShipmentStatus


@dataclass(frozen=True, slots=True)
class RecordShipmentEventCommand:
    tenant_id: UUID
    shipment_id: UUID
    event_type: ShipmentEventType
    occurred_at: datetime
    status: ShipmentStatus | None = None
    location_id: UUID | None = None
    description: str | None = None
    metadata: dict[str, object] | None = None
    created_by_user_id: UUID | None = None


class RecordShipmentEvent:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: RecordShipmentEventCommand,
    ) -> ShipmentEvent:
        description = command.description.strip() if command.description is not None else None

        async with self._unit_of_work as uow:
            shipment = await uow.shipments.get_by_id_and_tenant(
                command.shipment_id,
                command.tenant_id,
            )

            if shipment is None:
                raise ShipmentEventShipmentNotFoundError

            if command.location_id is not None:
                location = await uow.locations.get_by_id_and_tenant(
                    command.location_id,
                    command.tenant_id,
                )

                if location is None:
                    raise ShipmentEventLocationNotFoundError

            event = ShipmentEvent(
                tenant_id=command.tenant_id,
                shipment_id=command.shipment_id,
                event_type=command.event_type,
                status=command.status,
                location_id=command.location_id,
                description=description,
                occurred_at=command.occurred_at,
                metadata_=command.metadata,
                created_by_user_id=command.created_by_user_id,
            )

            uow.shipment_events.add(event)

            await uow.flush()
            await uow.commit()
            await uow.refresh(event)

            return event
