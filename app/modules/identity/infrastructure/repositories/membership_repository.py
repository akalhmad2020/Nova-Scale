from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.enums import MembershipStatus
from app.modules.identity.infrastructure.models.membership import Membership


class MembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        membership_id: UUID,
    ) -> Membership | None:
        statement = select(Membership).where(
            Membership.id == membership_id,
            Membership.deleted_at.is_(None),
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_user_and_tenant(
        self,
        user_id: UUID,
        tenant_id: UUID,
    ) -> Membership | None:
        statement = select(Membership).where(
            Membership.user_id == user_id,
            Membership.tenant_id == tenant_id,
            Membership.deleted_at.is_(None),
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: UUID,
    ) -> list[Membership]:
        statement = select(Membership).where(
            Membership.user_id == user_id,
            Membership.deleted_at.is_(None),
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    def add(self, membership: Membership) -> None:
        self._session.add(membership)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Membership]:
        statement = select(Membership).where(
            Membership.tenant_id == tenant_id,
            Membership.deleted_at.is_(None),
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    async def count_active_by_tenant(
        self,
        tenant_id: UUID,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.tenant_id == tenant_id,
                Membership.status == MembershipStatus.ACTIVE,
                Membership.deleted_at.is_(None),
            )
        )

        result = await self._session.execute(statement)
        return int(result.scalar_one())
