from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        index=True,
    )

    actor_type: Mapped[AuditActorType] = mapped_column(
        String(20),
        nullable=False,
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    resource_id: Mapped[UUID | None] = mapped_column(
        nullable=True,
    )

    outcome: Mapped[AuditOutcome] = mapped_column(
        String(20),
        nullable=False,
    )

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_audit_logs_tenant_id_id",
        ),
        Index(
            "ix_audit_logs_tenant_occurred",
            "tenant_id",
            "occurred_at",
        ),
        Index(
            "ix_audit_logs_tenant_resource",
            "tenant_id",
            "resource_type",
            "resource_id",
        ),
        Index(
            "ix_audit_logs_tenant_actor",
            "tenant_id",
            "actor_type",
            "actor_id",
        ),
        Index(
            "ix_audit_logs_tenant_action",
            "tenant_id",
            "action",
        ),
    )
