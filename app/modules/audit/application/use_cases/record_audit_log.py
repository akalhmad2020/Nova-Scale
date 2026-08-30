from datetime import UTC, datetime

from app.modules.audit.application.contracts import AuditRecord
from app.modules.audit.application.ports.repositories import (
    AuditLogRepository,
)
from app.modules.audit.domain.rules import (
    validate_audit_action,
    validate_audit_actor,
    validate_audit_resource_type,
)
from app.modules.audit.infrastructure.models.audit_log import AuditLog


class RecordAuditLogUseCase:
    def __init__(
        self,
        audit_logs: AuditLogRepository,
    ) -> None:
        self._audit_logs = audit_logs

    async def execute(
        self,
        record: AuditRecord,
    ) -> AuditLog:
        validate_audit_actor(
            actor_type=record.actor_type,
            actor_id=record.actor_id,
        )

        action = validate_audit_action(record.action)
        resource_type = validate_audit_resource_type(record.resource_type)

        occurred_at = record.occurred_at or datetime.now(UTC)

        audit_log = AuditLog(
            tenant_id=record.tenant_id,
            actor_type=record.actor_type,
            actor_id=record.actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=record.resource_id,
            outcome=record.outcome,
            metadata_=dict(record.metadata),
            occurred_at=occurred_at,
        )

        await self._audit_logs.add(audit_log)

        return audit_log
