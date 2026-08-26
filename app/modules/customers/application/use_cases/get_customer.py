from dataclasses import dataclass
from uuid import UUID

from app.modules.customers.application.exceptions import (
    CustomerNotFoundError,
)
from app.modules.customers.application.ports.unit_of_work import UnitOfWork
from app.modules.customers.infrastructure.models.customer import Customer


@dataclass(frozen=True, slots=True)
class GetCustomerQuery:
    tenant_id: UUID
    customer_id: UUID


class GetCustomer:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetCustomerQuery,
    ) -> Customer:
        async with self._unit_of_work as uow:
            customer = await uow.customers.get_by_id_and_tenant(
                query.customer_id,
                query.tenant_id,
            )

            if customer is None:
                raise CustomerNotFoundError

            return customer
