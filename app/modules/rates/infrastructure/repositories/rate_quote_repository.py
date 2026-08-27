from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rates.infrastructure.models.rate_quote import RateQuote


class RateQuoteRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_by_id_and_tenant(
        self,
        rate_quote_id: UUID,
        tenant_id: UUID,
    ) -> RateQuote | None:
        statement = select(RateQuote).where(
            RateQuote.id == rate_quote_id,
            RateQuote.tenant_id == tenant_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[RateQuote]:
        statement = (
            select(RateQuote)
            .where(
                RateQuote.tenant_id == tenant_id,
            )
            .order_by(
                RateQuote.created_at.desc(),
            )
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    async def list_by_shipment(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> list[RateQuote]:
        statement = (
            select(RateQuote)
            .where(
                RateQuote.shipment_id == shipment_id,
                RateQuote.tenant_id == tenant_id,
            )
            .order_by(
                RateQuote.created_at.desc(),
            )
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    def add(
        self,
        rate_quote: RateQuote,
    ) -> None:
        self._session.add(rate_quote)
