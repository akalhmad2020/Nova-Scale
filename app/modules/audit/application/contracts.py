from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.audit.domain.enums import AuditActorType, AuditOutcome


@dataclass(frozen=True, slots=True)
class AuditRecord:
    tenant_id: UUID
    actor_type: AuditActorType
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID | None
    outcome: AuditOutcome = AuditOutcome.SUCCESS
    metadata: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime | None = None
