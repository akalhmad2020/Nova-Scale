from typing import Protocol
from uuid import UUID

from app.modules.identity.infrastructure.models.role import Role


class RoleRepository(Protocol):
    async def get_by_id(
        self,
        role_id: UUID,
    ) -> Role | None: ...

    async def get_by_name(
        self,
        name: str,
    ) -> Role | None: ...

    def add(
        self,
        role: Role,
    ) -> None: ...
