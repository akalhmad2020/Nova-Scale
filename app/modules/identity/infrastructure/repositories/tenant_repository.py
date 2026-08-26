from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.infrastructure.models.tenant import Tenant


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        tenant_id: UUID,
    ) -> Tenant | None:
        statement = select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.deleted_at.is_(None),
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_slug(
        self,
        slug: str,
    ) -> Tenant | None:
        statement = select(Tenant).where(
            Tenant.slug == slug,
            Tenant.deleted_at.is_(None),
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    def add(self, tenant: Tenant) -> None:
        self._session.add(tenant)
