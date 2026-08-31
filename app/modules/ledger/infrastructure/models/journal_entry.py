from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class JournalEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "journal_entries"

    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    source_id: Mapped[UUID] = mapped_column(nullable=False)

    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="journal_entry_tenant_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "source_type",
            "source_id",
            name="journal_entry_tenant_source",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "source_type IN ('invoice_issued', 'invoice_voided', 'payment_posted')",
            name="journal_source_type",
        ),
        CheckConstraint(
            "btrim(description) <> ''",
            name="journal_description_not_blank",
        ),
        Index(
            "ix_journal_entries_tenant_posted_at",
            "tenant_id",
            "posted_at",
        ),
    )
