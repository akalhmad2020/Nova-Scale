from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.notifications.domain.enums import (
    NotificationChannel,
    NotificationStatus,
)
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    recipient: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=NotificationStatus.PENDING.value,
        server_default=NotificationStatus.PENDING.value,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="notification_tenant_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="notification_tenant_idempotency_key",
        ),
        CheckConstraint(
            "length(trim(event_type)) > 0",
            name="event_type_nonblank",
        ),
        CheckConstraint(
            "length(trim(recipient)) > 0",
            name="recipient_nonblank",
        ),
        CheckConstraint(
            "length(trim(body)) > 0",
            name="body_nonblank",
        ),
        CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="idempotency_key_nonblank",
        ),
        CheckConstraint(
            f"channel IN ('{NotificationChannel.EMAIL.value}', "
            f"'{NotificationChannel.WEBHOOK.value}')",
            name="channel_valid",
        ),
        CheckConstraint(
            f"status IN ('{NotificationStatus.PENDING.value}', "
            f"'{NotificationStatus.SENT.value}', "
            f"'{NotificationStatus.FAILED.value}')",
            name="status_valid",
        ),
        Index(
            "ix_notifications_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_notifications_tenant_scheduled_at",
            "tenant_id",
            "scheduled_at",
        ),
    )
