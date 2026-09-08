from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.saas.infrastructure.models.subscription import TenantSubscription


class SQLAlchemySubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_tenant(
        self,
        tenant_id: UUID,
    ) -> TenantSubscription | None:
        statement = select(TenantSubscription).where(
            TenantSubscription.tenant_id == tenant_id,
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    def add(
        self,
        subscription: TenantSubscription,
    ) -> None:
        self._session.add(subscription)
