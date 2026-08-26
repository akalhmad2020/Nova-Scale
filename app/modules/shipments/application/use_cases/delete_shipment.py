from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.shipments.application.exceptions import ShipmentNotFoundError
from app.modules.shipments.application.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class DeleteShipmentCommand:
    tenant_id: UUID
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

            shipment.deleted_at = datetime.now(UTC)

            await uow.flush()
            await uow.commit()
