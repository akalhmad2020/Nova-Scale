from typing import Protocol
from uuid import UUID

from app.modules.customers.infrastructure.models.customer import Customer


class CustomerRepository(Protocol):
    async def get_by_id(
        self,
        customer_id: UUID,
    ) -> Customer | None: ...

    async def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: UUID,
    ) -> Customer | None: ...

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Customer]: ...

    def add(
        self,
        customer: Customer,
    ) -> None: ...

    async def get_by_id_and_tenant(
        self,
        customer_id: UUID,
        tenant_id: UUID,
    ) -> Customer | None: ...
