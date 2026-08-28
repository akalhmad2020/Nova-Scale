from dataclasses import dataclass
from uuid import UUID

from app.modules.carriers.application.ports.unit_of_work import UnitOfWork
from app.modules.carriers.infrastructure.models.carrier import Carrier


@dataclass(frozen=True, slots=True)
class ListCarriersQuery:
    tenant_id: UUID


class ListCarriers:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: ListCarriersQuery,
    ) -> list[Carrier]:
        async with self._unit_of_work as uow:
            return await uow.carriers.list_by_tenant(
                query.tenant_id,
            )
