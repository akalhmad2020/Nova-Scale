from typing import Protocol
from uuid import UUID

from app.modules.identity.infrastructure.models.membership import Membership


class MembershipRepository(Protocol):
    async def get_by_id(
        self,
        membership_id: UUID,
    ) -> Membership | None: ...

    async def get_by_user_and_tenant(
        self,
        user_id: UUID,
        tenant_id: UUID,
    ) -> Membership | None: ...

    async def list_by_user(
        self,
        user_id: UUID,
    ) -> list[Membership]: ...

    def add(
        self,
        membership: Membership,
    ) -> None: ...

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Membership]: ...
