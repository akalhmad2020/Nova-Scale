from typing import Protocol
from uuid import UUID

from app.modules.identity.infrastructure.models.tenant import Tenant


class TenantRepository(Protocol):
    async def get_by_id(
        self,
        tenant_id: UUID,
    ) -> Tenant | None: ...

    async def get_by_slug(
        self,
        slug: str,
    ) -> Tenant | None: ...

    def add(
        self,
        tenant: Tenant,
    ) -> None: ...
