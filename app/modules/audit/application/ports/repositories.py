from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.audit.infrastructure.models.audit_log import AuditLog


class AuditLogRepository(Protocol):
    async def add(self, audit_log: AuditLog) -> None: ...

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        audit_log_id: UUID,
    ) -> AuditLog | None: ...

    async def list_for_tenant(
        self,
        *,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
        actor_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> Sequence[AuditLog]: ...
