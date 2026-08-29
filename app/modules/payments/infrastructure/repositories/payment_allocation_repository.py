from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payments.domain.enums import PaymentStatus
from app.modules.payments.infrastructure.models.payment import Payment
from app.modules.payments.infrastructure.models.payment_allocation import (
    PaymentAllocation,
)


class SQLAlchemyPaymentAllocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        payment_allocation: PaymentAllocation,
    ) -> None:
        self._session.add(payment_allocation)
        await self._session.flush()

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        payment_allocation_id: UUID,
    ) -> PaymentAllocation | None:
        statement = select(PaymentAllocation).where(
            PaymentAllocation.tenant_id == tenant_id,
            PaymentAllocation.id == payment_allocation_id,
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_payment_and_invoice(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
        invoice_id: UUID,
    ) -> PaymentAllocation | None:
        statement = select(PaymentAllocation).where(
            PaymentAllocation.tenant_id == tenant_id,
            PaymentAllocation.payment_id == payment_id,
            PaymentAllocation.invoice_id == invoice_id,
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_payment(
        self,
        *,
        tenant_id: UUID,
        payment_id: UUID,
    ) -> list[PaymentAllocation]:
        statement = (
            select(PaymentAllocation)
            .where(
                PaymentAllocation.tenant_id == tenant_id,
                PaymentAllocation.payment_id == payment_id,
            )
            .order_by(
                PaymentAllocation.created_at.asc(),
                PaymentAllocation.id.asc(),
            )
        )

        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_by_invoice(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> list[PaymentAllocation]:
        statement = (
            select(PaymentAllocation)
            .where(
                PaymentAllocation.tenant_id == tenant_id,
                PaymentAllocation.invoice_id == invoice_id,
            )
            .order_by(
                PaymentAllocation.created_at.asc(),
                PaymentAllocation.id.asc(),
            )
        )

        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def sum_posted_by_invoice(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Decimal:
        statement = (
            select(
                func.coalesce(
                    func.sum(PaymentAllocation.amount),
                    Decimal("0.00"),
                )
            )
            .join(
                Payment,
                Payment.id == PaymentAllocation.payment_id,
            )
            .where(
                PaymentAllocation.tenant_id == tenant_id,
                PaymentAllocation.invoice_id == invoice_id,
                Payment.tenant_id == tenant_id,
                Payment.status == PaymentStatus.POSTED,
            )
        )

        result = await self._session.execute(statement)
        return Decimal(result.scalar_one())

    async def delete(
        self,
        payment_allocation: PaymentAllocation,
    ) -> None:
        await self._session.delete(payment_allocation)
        await self._session.flush()
