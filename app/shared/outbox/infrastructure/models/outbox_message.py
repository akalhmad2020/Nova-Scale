from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.shared.outbox.domain.enums import OutboxMessageStatus


class OutboxMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "outbox_messages"

    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=OutboxMessageStatus.PENDING.value,
        server_default=OutboxMessageStatus.PENDING.value,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    available_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    claim_token: Mapped[UUID | None] = mapped_column(
        nullable=True,
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(event_type)) > 0",
            name="event_type_nonblank",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="attempt_count_nonnegative",
        ),
        CheckConstraint(
            f"status IN ('{OutboxMessageStatus.PENDING.value}', "
            f"'{OutboxMessageStatus.PROCESSING.value}', "
            f"'{OutboxMessageStatus.PROCESSED.value}', "
            f"'{OutboxMessageStatus.FAILED.value}')",
            name="status_valid",
        ),
        CheckConstraint(
            "("
            f"status = '{OutboxMessageStatus.PROCESSING.value}' "
            "AND claim_token IS NOT NULL "
            "AND lease_expires_at IS NOT NULL"
            ") OR ("
            f"status <> '{OutboxMessageStatus.PROCESSING.value}' "
            "AND claim_token IS NULL "
            "AND lease_expires_at IS NULL"
            ")",
            name="claim_status_consistent",
        ),
        Index(
            "ix_outbox_messages_status_available_at",
            "status",
            "available_at",
        ),
        Index(
            "ix_outbox_messages_status_lease_expires_at",
            "status",
            "lease_expires_at",
        ),
        Index(
            "ix_outbox_messages_tenant_created_at",
            "tenant_id",
            "created_at",
        ),
    )
