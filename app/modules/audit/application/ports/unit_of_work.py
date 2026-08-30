from types import TracebackType
from typing import Protocol

from app.modules.audit.application.ports.repositories import AuditLogRepository


class AuditUnitOfWork(Protocol):
    audit_logs: AuditLogRepository

    async def __aenter__(self) -> "AuditUnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
