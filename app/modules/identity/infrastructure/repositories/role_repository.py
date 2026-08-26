from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.infrastructure.models.role import Role


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        role_id: UUID,
    ) -> Role | None:
        statement = select(Role).where(
            Role.id == role_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        name: str,
    ) -> Role | None:
        statement = select(Role).where(
            Role.name == name,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    def add(self, role: Role) -> None:
        self._session.add(role)
