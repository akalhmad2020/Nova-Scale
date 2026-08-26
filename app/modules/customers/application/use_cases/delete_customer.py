from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.customers.application.exceptions import CustomerNotFoundError
from app.modules.customers.application.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class DeleteCustomerCommand:
    tenant_id: UUID
    customer_id: UUID


class DeleteCustomer:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: DeleteCustomerCommand,
    ) -> None:
        async with self._unit_of_work as uow:
            customer = await uow.customers.get_by_id_and_tenant(
                command.customer_id,
                command.tenant_id,
            )

            if customer is None:
                raise CustomerNotFoundError

            customer.deleted_at = datetime.now(UTC)

            await uow.flush()
            await uow.commit()
