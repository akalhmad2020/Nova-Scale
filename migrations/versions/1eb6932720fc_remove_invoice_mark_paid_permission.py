"""remove invoice mark paid permission

Revision ID: 1eb6932720fc
Revises: 248ab9e8bfac
Create Date: 2026-08-29 15:59:22.818139
"""

from collections.abc import Sequence

from alembic import op

revision: str = "1eb6932720fc"

down_revision: str | Sequence[str] | None = "248ab9e8bfac"

branch_labels: str | Sequence[str] | None = None

depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id
            FROM permissions
            WHERE code = 'invoice:mark_paid'
        )
        """
    )

    op.execute(
        """
        DELETE FROM permissions
        WHERE code = 'invoice:mark_paid'
        """
    )


def downgrade() -> None:
    pass
