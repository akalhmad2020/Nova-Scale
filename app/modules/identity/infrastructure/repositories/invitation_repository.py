from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.enums import InvitationStatus
from app.modules.identity.infrastructure.models.invitation import Invitation


class InvitationRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_by_id(
        self,
        invitation_id: UUID,
    ) -> Invitation | None:
        statement = select(Invitation).where(
            Invitation.id == invitation_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_pending_by_email_and_tenant(
        self,
        email: str,
        tenant_id: UUID,
    ) -> Invitation | None:
        statement = select(Invitation).where(
            Invitation.email == email,
            Invitation.tenant_id == tenant_id,
            Invitation.status == InvitationStatus.PENDING,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    def add(
        self,
        invitation: Invitation,
    ) -> None:
        self._session.add(invitation)
