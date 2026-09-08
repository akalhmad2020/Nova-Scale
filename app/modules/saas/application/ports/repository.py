from typing import Protocol
from uuid import UUID

from app.modules.saas.infrastructure.models.subscription import TenantSubscription


class SubscriptionRepository(Protocol):
    async def get_by_tenant(
        self,
        tenant_id: UUID,
    ) -> TenantSubscription | None: ...

    def add(
        self,
        subscription: TenantSubscription,
    ) -> None: ...
