from dataclasses import dataclass
from uuid import UUID

from app.modules.customers.application.exceptions import (
    CustomerCodeAlreadyExistsError,
)
from app.modules.customers.application.ports.unit_of_work import UnitOfWork
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer


@dataclass(frozen=True, slots=True)
class CreateCustomerCommand:
    tenant_id: UUID
    name: str
    code: str
    email: str | None = None
    phone: str | None = None
    notes: str | None = None


class CreateCustomer:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateCustomerCommand,
    ) -> Customer:
        name = command.name.strip()
        code = command.code.strip().upper()

        email = command.email.strip().lower() if command.email is not None else None

        phone = command.phone.strip() if command.phone is not None else None

        notes = command.notes.strip() if command.notes is not None else None

        async with self._unit_of_work as uow:
            existing_customer = await uow.customers.get_by_code_and_tenant(
                code,
                command.tenant_id,
            )

            if existing_customer is not None:
                raise CustomerCodeAlreadyExistsError

            customer = Customer(
                tenant_id=command.tenant_id,
                name=name,
                code=code,
                email=email,
                phone=phone,
                notes=notes,
                status=CustomerStatus.ACTIVE,
            )

            uow.customers.add(customer)

            await uow.flush()
            await uow.commit()

            return customer
