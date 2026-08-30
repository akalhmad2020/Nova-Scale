from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.infrastructure.models.audit_log import AuditLog


class SQLAlchemyAuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, audit_log: AuditLog) -> None:
        self._session.add(audit_log)
        await self._session.flush()

    async def get_by_id(
        self,
        *,
        tenant_id: UUID,
        audit_log_id: UUID,
    ) -> AuditLog | None:
        statement = select(AuditLog).where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.id == audit_log_id,
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

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
    ) -> Sequence[AuditLog]:
        statement = select(AuditLog).where(
            AuditLog.tenant_id == tenant_id,
        )

        if actor_id is not None:
            statement = statement.where(
                AuditLog.actor_id == actor_id,
            )

        if action is not None:
            statement = statement.where(
                AuditLog.action == action,
            )

        if resource_type is not None:
            statement = statement.where(
                AuditLog.resource_type == resource_type,
            )

        if resource_id is not None:
            statement = statement.where(
                AuditLog.resource_id == resource_id,
            )

        if occurred_from is not None:
            statement = statement.where(
                AuditLog.occurred_at >= occurred_from,
            )

        if occurred_to is not None:
            statement = statement.where(
                AuditLog.occurred_at <= occurred_to,
            )

        statement = (
            statement.order_by(
                AuditLog.occurred_at.desc(),
                AuditLog.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        result = await self._session.scalars(statement)
        return result.all()
