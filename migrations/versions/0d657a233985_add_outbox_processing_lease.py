"""add outbox processing lease

Revision ID: 0d657a233985
Revises: 8b479f4b2492
Create Date: 2026-08-29 22:03:24.871913
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0d657a233985"

down_revision: str | Sequence[str] | None = "8b479f4b2492"

branch_labels: str | Sequence[str] | None = None

depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outbox_messages",
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.drop_constraint(
        op.f("ck_outbox_messages_status_valid"),
        "outbox_messages",
        type_="check",
    )

    op.create_check_constraint(
        op.f("ck_outbox_messages_status_valid"),
        "outbox_messages",
        "status IN ('pending', 'processing', 'processed', 'failed')",
    )

    op.create_check_constraint(
        op.f("ck_outbox_messages_lease_status_consistent"),
        "outbox_messages",
        (
            "(status = 'processing' AND lease_expires_at IS NOT NULL) "
            "OR "
            "(status <> 'processing' AND lease_expires_at IS NULL)"
        ),
    )

    op.create_index(
        op.f("ix_outbox_messages_status_lease_expires_at"),
        "outbox_messages",
        ["status", "lease_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_outbox_messages_status_lease_expires_at"),
        table_name="outbox_messages",
    )

    op.drop_constraint(
        op.f("ck_outbox_messages_lease_status_consistent"),
        "outbox_messages",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_outbox_messages_status_valid"),
        "outbox_messages",
        type_="check",
    )

    op.create_check_constraint(
        op.f("ck_outbox_messages_status_valid"),
        "outbox_messages",
        "status IN ('pending', 'processed', 'failed')",
    )

    op.drop_column(
        "outbox_messages",
        "lease_expires_at",
    )
