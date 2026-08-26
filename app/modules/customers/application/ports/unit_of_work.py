from types import TracebackType
from typing import Protocol

from app.modules.customers.application.ports.customer_repository import (
    CustomerRepository,
)
from app.modules.customers.infrastructure.models.customer import Customer


class UnitOfWork(Protocol):
    @property
    def customers(self) -> CustomerRepository: ...

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def flush(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def refresh(
        self,
        customer: Customer,
    ) -> None: ...
