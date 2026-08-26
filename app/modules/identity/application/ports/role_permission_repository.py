from typing import Protocol
from uuid import UUID

from app.modules.identity.infrastructure.models.role_permission import (
    RolePermission,
)


class RolePermissionRepository(Protocol):
    async def has_permission(
        self,
        role_id: UUID,
        permission_code: str,
    ) -> bool: ...

    def add(
        self,
        role_permission: RolePermission,
    ) -> None: ...
