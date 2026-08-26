from typing import Protocol
from uuid import UUID

from app.modules.identity.infrastructure.models.invitation import Invitation


class InvitationRepository(Protocol):
    async def get_by_id(
        self,
        invitation_id: UUID,
    ) -> Invitation | None: ...

    async def get_pending_by_email_and_tenant(
        self,
        email: str,
        tenant_id: UUID,
    ) -> Invitation | None: ...

    def add(
        self,
        invitation: Invitation,
    ) -> None: ...
