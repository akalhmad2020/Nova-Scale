from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.carriers.infrastructure.models.carrier import Carrier


class CarrierRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_by_id_and_tenant(
        self,
        carrier_id: UUID,
        tenant_id: UUID,
    ) -> Carrier | None:
        statement = select(Carrier).where(
            Carrier.id == carrier_id,
            Carrier.tenant_id == tenant_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: UUID,
    ) -> Carrier | None:
        statement = select(Carrier).where(
            Carrier.code == code,
            Carrier.tenant_id == tenant_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Carrier]:
        statement = (
            select(Carrier)
            .where(
                Carrier.tenant_id == tenant_id,
            )
            .order_by(
                Carrier.created_at.desc(),
            )
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    def add(
        self,
        carrier: Carrier,
    ) -> None:
        self._session.add(carrier)
