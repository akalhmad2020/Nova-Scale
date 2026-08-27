from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.shipment_events.infrastructure.models.shipment_event import (
    ShipmentEvent,
)


class ShipmentEventRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def list_by_shipment(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> list[ShipmentEvent]:
        statement = (
            select(ShipmentEvent)
            .where(
                ShipmentEvent.shipment_id == shipment_id,
                ShipmentEvent.tenant_id == tenant_id,
            )
            .order_by(
                ShipmentEvent.occurred_at.asc(),
                ShipmentEvent.created_at.asc(),
            )
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    def add(
        self,
        event: ShipmentEvent,
    ) -> None:
        self._session.add(event)
