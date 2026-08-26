from typing import Protocol
from uuid import UUID

from app.modules.identity.infrastructure.models.auth_session import AuthSession


class AuthSessionRepository(Protocol):
    async def get_by_id(
        self,
        session_id: UUID,
    ) -> AuthSession | None: ...

    async def get_by_refresh_token_hash(
        self,
        refresh_token_hash: str,
    ) -> AuthSession | None: ...

    async def get_by_refresh_token_hash_for_update(
        self,
        refresh_token_hash: str,
    ) -> AuthSession | None: ...

    def add(
        self,
        auth_session: AuthSession,
    ) -> None: ...
