from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.locations.infrastructure.models.location import Location


class LocationRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_by_id(
        self,
        location_id: UUID,
    ) -> Location | None:
        statement = select(Location).where(
            Location.id == location_id,
            Location.deleted_at.is_(None),
        )

        location = await self._session.scalar(statement)

        return location

    async def get_by_id_and_tenant(
        self,
        location_id: UUID,
        tenant_id: UUID,
    ) -> Location | None:
        statement = select(Location).where(
            Location.id == location_id,
            Location.tenant_id == tenant_id,
            Location.deleted_at.is_(None),
        )

        location = await self._session.scalar(statement)

        return location

    async def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: UUID,
    ) -> Location | None:
        statement = select(Location).where(
            Location.code == code,
            Location.tenant_id == tenant_id,
            Location.deleted_at.is_(None),
        )

        location = await self._session.scalar(statement)

        return location

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Location]:
        statement = (
            select(Location)
            .where(
                Location.tenant_id == tenant_id,
                Location.deleted_at.is_(None),
            )
            .order_by(Location.created_at)
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    def add(
        self,
        location: Location,
    ) -> None:
        self._session.add(location)
