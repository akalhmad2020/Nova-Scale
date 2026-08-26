from dataclasses import dataclass
from uuid import UUID

from app.modules.customers.application.exceptions import (
    CustomerCodeAlreadyExistsError,
    CustomerNotFoundError,
)
from app.modules.customers.application.ports.unit_of_work import UnitOfWork
from app.modules.customers.infrastructure.models.customer import Customer


@dataclass(frozen=True, slots=True)
class UpdateCustomerCommand:
    tenant_id: UUID
    customer_id: UUID
    name: str
    code: str
    email: str | None = None
    phone: str | None = None
    notes: str | None = None


class UpdateCustomer:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: UpdateCustomerCommand,
    ) -> Customer:
        name = command.name.strip()
        code = command.code.strip().upper()

        email = command.email.strip().lower() if command.email is not None else None

        phone = command.phone.strip() if command.phone is not None else None

        notes = command.notes.strip() if command.notes is not None else None

        async with self._unit_of_work as uow:
            customer = await uow.customers.get_by_id_and_tenant(
                command.customer_id,
                command.tenant_id,
            )

            if customer is None:
                raise CustomerNotFoundError

            existing = await uow.customers.get_by_code_and_tenant(
                code,
                command.tenant_id,
            )

            if existing is not None and existing.id != customer.id:
                raise CustomerCodeAlreadyExistsError

            customer.name = name
            customer.code = code
            customer.email = email
            customer.phone = phone
            customer.notes = notes

            await uow.flush()
            await uow.commit()
            await uow.refresh(customer)
            return customer
