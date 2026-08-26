from dataclasses import dataclass
from uuid import UUID

from app.modules.customers.application.ports.unit_of_work import UnitOfWork
from app.modules.customers.infrastructure.models.customer import Customer


@dataclass(frozen=True, slots=True)
class ListCustomersQuery:
    tenant_id: UUID


class ListCustomers:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: ListCustomersQuery,
    ) -> list[Customer]:
        async with self._unit_of_work as uow:
            return await uow.customers.list_by_tenant(
                query.tenant_id,
            )
