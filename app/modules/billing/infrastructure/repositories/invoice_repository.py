from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.infrastructure.models.invoice import Invoice


class SQLAlchemyInvoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, invoice: Invoice) -> None:
        self._session.add(invoice)

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Invoice | None:
        statement = select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.id == invoice_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_number(
        self,
        *,
        tenant_id: UUID,
        invoice_number: str,
    ) -> Invoice | None:
        statement = select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_number == invoice_number,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        *,
        tenant_id: UUID,
    ) -> Sequence[Invoice]:
        statement = (
            select(Invoice)
            .where(
                Invoice.tenant_id == tenant_id,
            )
            .order_by(Invoice.created_at.desc())
        )

        result = await self._session.execute(statement)

        return result.scalars().all()

    async def refresh(
        self,
        invoice: Invoice,
    ) -> None:
        await self._session.refresh(invoice)

    async def get_by_id_for_update(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Invoice | None:
        statement = (
            select(Invoice)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.id == invoice_id,
            )
            .with_for_update()
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
