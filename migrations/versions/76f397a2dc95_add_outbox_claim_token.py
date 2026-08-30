"""add outbox claim token

Revision ID: 76f397a2dc95
Revises: 0d657a233985
Create Date: 2026-08-29 22:14:15.737572
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "76f397a2dc95"

down_revision: str | Sequence[str] | None = "0d657a233985"

branch_labels: str | Sequence[str] | None = None

depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outbox_messages",
        sa.Column(
            "claim_token",
            sa.Uuid(),
            nullable=True,
        ),
    )

    op.drop_constraint(
        op.f("ck_outbox_messages_lease_status_consistent"),
        "outbox_messages",
        type_="check",
    )

    op.execute(
        sa.text(
            """
            UPDATE outbox_messages
            SET claim_token = gen_random_uuid()
            WHERE status = 'processing'
              AND claim_token IS NULL
            """
        )
    )

    op.create_check_constraint(
        op.f("ck_outbox_messages_claim_status_consistent"),
        "outbox_messages",
        (
            "(status = 'processing' "
            "AND claim_token IS NOT NULL "
            "AND lease_expires_at IS NOT NULL) "
            "OR "
            "(status <> 'processing' "
            "AND claim_token IS NULL "
            "AND lease_expires_at IS NULL)"
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_outbox_messages_claim_status_consistent"),
        "outbox_messages",
        type_="check",
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

    op.drop_column(
        "outbox_messages",
        "claim_token",
    )
