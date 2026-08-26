from dataclasses import dataclass
from uuid import UUID

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

            if not can_transition_shipment_status(
                shipment.status,
                command.target_status,
            ):
                raise InvalidShipmentStatusTransitionError

            shipment.status = command.target_status

            await uow.flush()
            await uow.commit()
            await uow.refresh(shipment)

            return shipment
