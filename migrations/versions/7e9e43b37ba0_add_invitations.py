"""add invitations

Revision ID: 7e9e43b37ba0
Revises: b3611e289641
Create Date: 2026-08-25 18:56:32.614874
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "7e9e43b37ba0"
down_revision: str | Sequence[str] | None = "b3611e289641"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


invitation_status = postgresql.ENUM(
    "pending",
    "accepted",
    "revoked",
    "expired",
    name="invitation_status",
)


def upgrade() -> None:
    op.create_table(
        "invitations",
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.String(length=320),
            nullable=False,
        ),
        sa.Column(
            "status",
            invitation_status,
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("uuidv7()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_invitations_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_invitations_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_invitations"),
        ),
    )

    op.create_index(
        "ix_invitations_email",
        "invitations",
        ["email"],
        unique=False,
    )

    op.create_index(
        "ix_invitations_tenant_id",
        "invitations",
        ["tenant_id"],
        unique=False,
    )

    op.create_index(
        "uq_invitations_pending_tenant_email",
        "invitations",
        ["tenant_id", "email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_invitations_pending_tenant_email",
        table_name="invitations",
    )

    op.drop_index(
        "ix_invitations_tenant_id",
        table_name="invitations",
    )

    op.drop_index(
        "ix_invitations_email",
        table_name="invitations",
    )

    op.drop_table("invitations")
