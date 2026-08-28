from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.infrastructure.models.shipment_label import ShipmentLabel


class ShipmentLabelRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_by_id_and_tenant(
        self,
        shipment_label_id: UUID,
        tenant_id: UUID,
    ) -> ShipmentLabel | None:
        statement = select(ShipmentLabel).where(
            ShipmentLabel.id == shipment_label_id,
            ShipmentLabel.tenant_id == tenant_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def list_by_shipment(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> list[ShipmentLabel]:
        statement = (
            select(ShipmentLabel)
            .where(
                ShipmentLabel.shipment_id == shipment_id,
                ShipmentLabel.tenant_id == tenant_id,
            )
            .order_by(
                ShipmentLabel.created_at.desc(),
            )
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    def add(
        self,
        shipment_label: ShipmentLabel,
    ) -> None:
        self._session.add(shipment_label)
