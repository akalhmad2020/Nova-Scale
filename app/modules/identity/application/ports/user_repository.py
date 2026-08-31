from typing import Protocol
from uuid import UUID

from app.modules.identity.infrastructure.models.user import User


class UserRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_by_email_for_update(
        self,
        email: str,
    ) -> User | None: ...

    async def email_exists(self, email: str) -> bool: ...

    def add(self, user: User) -> None: ...
