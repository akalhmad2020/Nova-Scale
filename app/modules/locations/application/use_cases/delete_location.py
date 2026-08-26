from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.locations.application.exceptions import LocationNotFoundError
from app.modules.locations.application.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class DeleteLocationCommand:
    tenant_id: UUID
    location_id: UUID


class DeleteLocation:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: DeleteLocationCommand,
    ) -> None:
        async with self._unit_of_work as uow:
            location = await uow.locations.get_by_id_and_tenant(
                command.location_id,
                command.tenant_id,
            )

            if location is None:
                raise LocationNotFoundError

            location.deleted_at = datetime.now(UTC)

            await uow.flush()
            await uow.commit()
