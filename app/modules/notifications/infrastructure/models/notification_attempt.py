from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.notifications.domain.enums import NotificationAttemptStatus
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class NotificationAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_attempts"

    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    notification_id: Mapped[UUID] = mapped_column(nullable=False)

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    provider_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="notification_attempt_tenant_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "notification_id",
            "attempt_number",
            name="notification_attempt_number",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "notification_id"],
            ["notifications.tenant_id", "notifications.id"],
            name="notification_attempt_notification_fk",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "attempt_number > 0",
            name="attempt_number_positive",
        ),
        CheckConstraint(
            "length(trim(provider)) > 0",
            name="provider_nonblank",
        ),
        CheckConstraint(
            f"status IN ('{NotificationAttemptStatus.SUCCESS.value}', "
            f"'{NotificationAttemptStatus.FAILED.value}')",
            name="status_valid",
        ),
        Index(
            "ix_notification_attempts_tenant_notification",
            "tenant_id",
            "notification_id",
        ),
        Index(
            "ix_notification_attempts_tenant_attempted_at",
            "tenant_id",
            "attempted_at",
        ),
    )
