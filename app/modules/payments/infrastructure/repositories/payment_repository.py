from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payments.infrastructure.models.payment import Payment


class SQLAlchemyPaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, payment: Payment) -> None:
        self._session.add(payment)
        await self._session.flush()

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
    ) -> Payment | None:
        stmt = select(Payment).where(
            Payment.tenant_id == tenant_id,
            Payment.id == payment_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_number(
        self,
        *,
        tenant_id: UUID,
        payment_number: str,
    ) -> Payment | None:
        stmt = select(Payment).where(
            Payment.tenant_id == tenant_id,
            Payment.payment_number == payment_number,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        *,
        tenant_id: UUID,
    ) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.tenant_id == tenant_id)
            .order_by(Payment.created_at.desc(), Payment.id.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def refresh(self, payment: Payment) -> None:
        await self._session.refresh(payment)

    async def get_by_id_for_update(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
    ) -> Payment | None:
        statement = (
            select(Payment)
            .where(
                Payment.tenant_id == tenant_id,
                Payment.id == payment_id,
            )
            .with_for_update()
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
