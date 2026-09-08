from uuid import UUID

from sqlalchemy import func, select
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

    async def get_by_token_hash(
        self,
        token_hash: str,
    ) -> Invitation | None:
        statement = select(Invitation).where(
            Invitation.token_hash == token_hash,
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

    async def count_pending_by_tenant(
        self,
        tenant_id: UUID,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(Invitation)
            .where(
                Invitation.tenant_id == tenant_id,
                Invitation.status == InvitationStatus.PENDING,
            )
        )

        result = await self._session.execute(statement)
        return int(result.scalar_one())

    def add(
        self,
        invitation: Invitation,
    ) -> None:
        self._session.add(invitation)
