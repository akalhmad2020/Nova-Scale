from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customers.infrastructure.models.customer import Customer


class CustomerRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_by_id(
        self,
        customer_id: UUID,
    ) -> Customer | None:
        statement = select(Customer).where(
            Customer.id == customer_id,
            Customer.deleted_at.is_(None),
        )

        customer = await self._session.scalar(statement)

        return customer

    async def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: UUID,
    ) -> Customer | None:
        statement = select(Customer).where(
            Customer.tenant_id == tenant_id,
            Customer.code == code,
            Customer.deleted_at.is_(None),
        )

        customer = await self._session.scalar(statement)

        return customer

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Customer]:
        statement = (
            select(Customer)
            .where(
                Customer.tenant_id == tenant_id,
                Customer.deleted_at.is_(None),
            )
            .order_by(Customer.created_at)
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    def add(
        self,
        customer: Customer,
    ) -> None:
        self._session.add(customer)

    async def get_by_id_and_tenant(
        self,
        customer_id: UUID,
        tenant_id: UUID,
    ) -> Customer | None:
        statement = select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
            Customer.deleted_at.is_(None),
        )

        customer = await self._session.scalar(statement)

        return customer
