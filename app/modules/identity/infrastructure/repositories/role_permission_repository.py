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

    async def list_permission_codes(
        self,
        role_id: UUID,
    ) -> set[str]:
        statement = (
            select(Permission.code)
            .join(
                RolePermission,
                RolePermission.permission_id == Permission.id,
            )
            .where(
                RolePermission.role_id == role_id,
            )
        )

        result = await self._session.scalars(statement)

        return set(result.all())

    def add(
        self,
        role_permission: RolePermission,
    ) -> None:
        self._session.add(role_permission)

    async def remove_permission(
        self,
        role_id: UUID,
        permission_code: str,
    ) -> None:
        statement = (
            select(RolePermission)
            .join(
                Permission,
                Permission.id == RolePermission.permission_id,
            )
            .where(
                RolePermission.role_id == role_id,
                Permission.code == permission_code,
            )
        )

        role_permission = await self._session.scalar(statement)

        if role_permission is not None:
            await self._session.delete(role_permission)
