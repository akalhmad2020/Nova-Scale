"""add invitation token hash

Revision ID: 996bf46e4af9
Revises: 6980f5562a4b
Create Date: 2026-09-07 15:36:37.664941
"""

import secrets
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "996bf46e4af9"
down_revision: str | Sequence[str] | None = "6980f5562a4b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "invitations",
        sa.Column(
            "token_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )

    connection = op.get_bind()

    invitation_ids = connection.execute(
        sa.text(
            """
            SELECT id
            FROM invitations
            WHERE token_hash IS NULL
            """
        )
    ).scalars()

    for invitation_id in invitation_ids:
        connection.execute(
            sa.text(
                """
                UPDATE invitations
                SET token_hash = :token_hash
                WHERE id = :invitation_id
                """
            ),
            {
                "invitation_id": invitation_id,
                "token_hash": secrets.token_hex(32),
            },
        )

    op.alter_column(
        "invitations",
        "token_hash",
        existing_type=sa.String(length=64),
        nullable=False,
    )

    op.create_unique_constraint(
        "uq_invitations_token_hash",
        "invitations",
        ["token_hash"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_invitations_token_hash",
        "invitations",
        type_="unique",
    )

    op.drop_column(
        "invitations",
        "token_hash",
    )
