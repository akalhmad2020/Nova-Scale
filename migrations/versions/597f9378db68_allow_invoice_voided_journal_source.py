"""allow invoice voided journal source

Revision ID: 597f9378db68
Revises: f8fb83e494c1
Create Date: 2026-08-30 18:54:08.873692
"""

from collections.abc import Sequence

from alembic import op


revision: str = "597f9378db68"
down_revision: str | Sequence[str] | None = "f8fb83e494c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_journal_entries_journal_source_type"),
        "journal_entries",
        type_="check",
    )

    op.create_check_constraint(
        "journal_source_type",
        "journal_entries",
        """
        source_type IN (
            'invoice_issued',
            'invoice_voided',
            'payment_posted'
        )
        """,
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_journal_entries_journal_source_type"),
        "journal_entries",
        type_="check",
    )

    op.create_check_constraint(
        "journal_source_type",
        "journal_entries",
        """
        source_type IN (
            'invoice_issued',
            'payment_posted'
        )
        """,
    )