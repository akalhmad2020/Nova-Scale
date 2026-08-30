from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyAuditLogRepository,
)


class SQLAlchemyAuditUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.audit_logs = SQLAlchemyAuditLogRepository(session)

    async def __aenter__(self) -> "SQLAlchemyAuditUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
