from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)


class CarrierServiceRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_by_id_and_tenant(
        self,
        carrier_service_id: UUID,
        tenant_id: UUID,
    ) -> CarrierService | None:
        statement = select(CarrierService).where(
            CarrierService.id == carrier_service_id,
            CarrierService.tenant_id == tenant_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_code_and_carrier(
        self,
        *,
        tenant_id: UUID,
        carrier_id: UUID,
        code: str,
    ) -> CarrierService | None:
        statement = select(CarrierService).where(
            CarrierService.tenant_id == tenant_id,
            CarrierService.carrier_id == carrier_id,
            CarrierService.code == code,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def list_by_carrier(
        self,
        *,
        tenant_id: UUID,
        carrier_id: UUID,
    ) -> list[CarrierService]:
        statement = (
            select(CarrierService)
            .where(
                CarrierService.tenant_id == tenant_id,
                CarrierService.carrier_id == carrier_id,
            )
            .order_by(
                CarrierService.created_at.desc(),
            )
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    def add(
        self,
        carrier_service: CarrierService,
    ) -> None:
        self._session.add(carrier_service)
