from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class AIConversation(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "ai_conversations"
    __table_args__ = (
        Index(
            "ix_ai_conversations_tenant_user_updated_at",
            "tenant_id",
            "user_id",
            "updated_at",
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

    title: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    continuation_kind: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
    )

    continuation_route: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
    )

    continuation_original_identifier: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )


class AIConversationMessage(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "ai_conversation_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="role",
        ),
        Index(
            "ix_ai_conversation_messages_conversation_created_at",
            "conversation_id",
            "created_at",
        ),
        Index(
            "ix_ai_conversation_messages_tenant_id",
            "tenant_id",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
