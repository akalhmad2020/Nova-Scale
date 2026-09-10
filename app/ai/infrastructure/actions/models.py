from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AIAgentAction(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "ai_agent_actions"
    __table_args__ = (
        CheckConstraint(
            "action_type IN ('transition_shipment_status', 'update_shipment_notes')",
            name="action_type",
        ),
        CheckConstraint(
            "status IN ('pending_confirmation', 'executing', 'executed', 'cancelled', 'failed')",
            name="status",
        ),
        CheckConstraint(
            "resource_type = 'shipment'",
            name="resource_type",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_ai_agent_actions_idempotency_key",
        ),
        Index(
            "ix_ai_agent_actions_tenant_user_created_at",
            "tenant_id",
            "user_id",
            "created_at",
        ),
        Index(
            "ix_ai_agent_actions_conversation_created_at",
            "conversation_id",
            "created_at",
        ),
        Index(
            "uq_ai_agent_actions_active_conversation",
            "conversation_id",
            unique=True,
            postgresql_where=text("status IN ('pending_confirmation', 'executing')"),
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    idempotency_key: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="pending_confirmation",
    )

    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="shipment",
    )

    resource_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    shipment_identifier: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    expected_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    target_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
    )

    expected_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    new_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    result_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
