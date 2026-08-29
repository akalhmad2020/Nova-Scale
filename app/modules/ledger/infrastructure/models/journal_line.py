from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class JournalLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "journal_lines"

    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    journal_entry_id: Mapped[UUID] = mapped_column(nullable=False)

    ledger_account_id: Mapped[UUID] = mapped_column(nullable=False)

    debit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="journal_line_tenant_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "journal_entry_id"],
            ["journal_entries.tenant_id", "journal_entries.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "ledger_account_id"],
            ["ledger_accounts.tenant_id", "ledger_accounts.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "debit >= 0",
            name="journal_line_debit_non_negative",
        ),
        CheckConstraint(
            "credit >= 0",
            name="journal_line_credit_non_negative",
        ),
        CheckConstraint(
            """
            (
                debit > 0
                AND credit = 0
            )
            OR
            (
                credit > 0
                AND debit = 0
            )
            """,
            name="journal_line_one_side_only",
        ),
        Index(
            "ix_journal_lines_tenant_entry",
            "tenant_id",
            "journal_entry_id",
        ),
        Index(
            "ix_journal_lines_tenant_account",
            "tenant_id",
            "ledger_account_id",
        ),
    )
