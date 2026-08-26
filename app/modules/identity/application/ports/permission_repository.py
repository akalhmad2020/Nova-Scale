from typing import Protocol
from uuid import UUID

from app.modules.identity.infrastructure.models.permission import Permission


class PermissionRepository(Protocol):
    async def get_by_id(
        self,
        permission_id: UUID,
    ) -> Permission | None: ...

    async def get_by_code(
        self,
        code: str,
    ) -> Permission | None: ...

    def add(
        self,
        permission: Permission,
    ) -> None: ...
