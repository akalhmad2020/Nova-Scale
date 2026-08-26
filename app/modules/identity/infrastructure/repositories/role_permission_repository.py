from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.infrastructure.models.permission import Permission
from app.modules.identity.infrastructure.models.role_permission import (
    RolePermission,
)


class RolePermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_permission(
        self,
        role_id: UUID,
        permission_code: str,
    ) -> bool:
        statement = (
            select(RolePermission.role_id)
            .join(
                Permission,
                Permission.id == RolePermission.permission_id,
            )
            .where(
                RolePermission.role_id == role_id,
                Permission.code == permission_code,
            )
            .limit(1)
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none() is not None

    def add(
        self,
        role_permission: RolePermission,
    ) -> None:
        self._session.add(role_permission)
