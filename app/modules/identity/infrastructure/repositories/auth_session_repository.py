from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.infrastructure.models.auth_session import AuthSession


class AuthSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, session_id: UUID) -> AuthSession | None:
        statement = select(AuthSession).where(
            AuthSession.id == session_id,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_refresh_token_hash(
        self,
        refresh_token_hash: str,
    ) -> AuthSession | None:
        statement = select(AuthSession).where(
            AuthSession.refresh_token_hash == refresh_token_hash,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_refresh_token_hash_for_update(
        self,
        refresh_token_hash: str,
    ) -> AuthSession | None:
        statement = (
            select(AuthSession)
            .where(
                AuthSession.refresh_token_hash == refresh_token_hash,
            )
            .with_for_update()
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    def add(self, auth_session: AuthSession) -> None:
        self._session.add(auth_session)
