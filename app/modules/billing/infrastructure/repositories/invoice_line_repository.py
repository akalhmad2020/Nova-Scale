from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.infrastructure.models.invoice_line import InvoiceLine


class SQLAlchemyInvoiceLineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        invoice_line: InvoiceLine,
    ) -> None:
        self._session.add(invoice_line)
        await self._session.flush()

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        invoice_line_id: UUID,
    ) -> InvoiceLine | None:
        statement = select(InvoiceLine).where(
            InvoiceLine.tenant_id == tenant_id,
            InvoiceLine.id == invoice_line_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def list_by_invoice(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Sequence[InvoiceLine]:
        statement = (
            select(InvoiceLine)
            .where(
                InvoiceLine.tenant_id == tenant_id,
                InvoiceLine.invoice_id == invoice_id,
            )
            .order_by(InvoiceLine.created_at.asc())
        )

        result = await self._session.execute(statement)

        return result.scalars().all()

    async def delete(
        self,
        invoice_line: InvoiceLine,
    ) -> None:
        await self._session.delete(invoice_line)
