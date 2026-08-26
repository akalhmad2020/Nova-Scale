from types import TracebackType
from uuid import UUID

from app.modules.customers.infrastructure.models.customer import Customer


class FakeCustomerRepository:
    def __init__(self) -> None:
        self.customers: list[Customer] = []

    async def get_by_id(
        self,
        customer_id: UUID,
    ) -> Customer | None:
        return next(
            (
                customer
                for customer in self.customers
                if customer.id == customer_id and customer.deleted_at is None
            ),
            None,
        )

    async def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: UUID,
    ) -> Customer | None:
        return next(
            (
                customer
                for customer in self.customers
                if customer.code == code
                and customer.tenant_id == tenant_id
                and customer.deleted_at is None
            ),
            None,
        )

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Customer]:
        return [
            customer
            for customer in self.customers
            if customer.tenant_id == tenant_id and customer.deleted_at is None
        ]

    def add(
        self,
        customer: Customer,
    ) -> None:

        self.customers.append(customer)

    async def get_by_id_and_tenant(
        self,
        customer_id: UUID,
        tenant_id: UUID,
    ) -> Customer | None:
        return next(
            (
                customer
                for customer in self.customers
                if customer.id == customer_id
                and customer.tenant_id == tenant_id
                and customer.deleted_at is None
            ),
            None,
        )


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.customers = FakeCustomerRepository()

        self.flushed = False
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def flush(self) -> None:
        self.flushed = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(
        self,
        customer: Customer,
    ) -> None:
        return None
