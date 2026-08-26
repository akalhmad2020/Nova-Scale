from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.infrastructure.models.permission import Permission


class PermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        permission_id: UUID,
    ) -> Permission | None:
        statement = select(Permission).where(
            Permission.id == permission_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_code(
        self,
        code: str,
    ) -> Permission | None:
        statement = select(Permission).where(
            Permission.code == code,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    def add(self, permission: Permission) -> None:
        self._session.add(permission)
