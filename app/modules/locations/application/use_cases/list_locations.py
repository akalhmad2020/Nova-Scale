from dataclasses import dataclass
from uuid import UUID

from app.modules.locations.application.ports.unit_of_work import UnitOfWork
from app.modules.locations.infrastructure.models.location import Location


@dataclass(frozen=True, slots=True)
class ListLocationsQuery:
    tenant_id: UUID


class ListLocations:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: ListLocationsQuery,
    ) -> list[Location]:
        async with self._unit_of_work as uow:
            return await uow.locations.list_by_tenant(
                query.tenant_id,
            )
