from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.infrastructure.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        statement = select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(
            User.email == email,
            User.deleted_at.is_(None),
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        statement = select(User.id).where(
            User.email == email,
            User.deleted_at.is_(None),
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none() is not None

    def add(self, user: User) -> None:
        self._session.add(user)

    async def get_by_email_for_update(
        self,
        email: str,
    ) -> User | None:
        statement = (
            select(User)
            .where(
                User.email == email,
                User.deleted_at.is_(None),
            )
            .with_for_update()
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()
