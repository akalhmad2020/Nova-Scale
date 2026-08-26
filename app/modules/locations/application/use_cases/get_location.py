from dataclasses import dataclass
from uuid import UUID

from app.modules.locations.application.exceptions import LocationNotFoundError
from app.modules.locations.application.ports.unit_of_work import UnitOfWork
from app.modules.locations.infrastructure.models.location import Location


@dataclass(frozen=True, slots=True)
class GetLocationQuery:
    tenant_id: UUID
    location_id: UUID


class GetLocation:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetLocationQuery,
    ) -> Location:
        async with self._unit_of_work as uow:
            location = await uow.locations.get_by_id_and_tenant(
                query.location_id,
                query.tenant_id,
            )

            if location is None:
                raise LocationNotFoundError

            return location
