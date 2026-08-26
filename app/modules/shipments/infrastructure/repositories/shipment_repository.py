from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.shipments.infrastructure.models.shipment import Shipment


class ShipmentRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_by_id_and_tenant(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> Shipment | None:
        statement = select(Shipment).where(
            Shipment.id == shipment_id,
            Shipment.tenant_id == tenant_id,
            Shipment.deleted_at.is_(None),
        )

        shipment = await self._session.scalar(statement)

        return shipment

    async def get_by_tracking_number_and_tenant(
        self,
        tracking_number: str,
        tenant_id: UUID,
    ) -> Shipment | None:
        statement = select(Shipment).where(
            Shipment.tracking_number == tracking_number,
            Shipment.tenant_id == tenant_id,
            Shipment.deleted_at.is_(None),
        )

        shipment = await self._session.scalar(statement)

        return shipment

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Shipment]:
        statement = (
            select(Shipment)
            .where(
                Shipment.tenant_id == tenant_id,
                Shipment.deleted_at.is_(None),
            )
            .order_by(Shipment.created_at)
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    def add(
        self,
        shipment: Shipment,
    ) -> None:
        self._session.add(shipment)
