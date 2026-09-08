"""add saas subscription foundation

Revision ID: c4f2a1b7e903
Revises: 996bf46e4af9
Create Date: 2026-09-07 22:50:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4f2a1b7e903"
down_revision: str | Sequence[str] | None = "996bf46e4af9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PLAN_VALUES = ("starter", "professional", "enterprise")
STATUS_VALUES = ("active", "past_due", "canceled", "suspended")


def upgrade() -> None:
    bind = op.get_bind()

    plan_enum = postgresql.ENUM(*PLAN_VALUES, name="saas_plan_code")
    status_enum = postgresql.ENUM(*STATUS_VALUES, name="saas_subscription_status")
    plan_enum.create(bind, checkfirst=True)
    status_enum.create(bind, checkfirst=True)

    op.create_table(
        "tenant_subscriptions",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "plan_code",
            postgresql.ENUM(*PLAN_VALUES, name="saas_plan_code", create_type=False),
            server_default=sa.text("'starter'::saas_plan_code"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                *STATUS_VALUES,
                name="saas_subscription_status",
                create_type=False,
            ),
            server_default=sa.text("'active'::saas_subscription_status"),
            nullable=False,
        ),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("provider_customer_id", sa.String(length=255), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=255), nullable=True),
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
        sa.CheckConstraint(
            "plan_code IN ('starter', 'professional', 'enterprise')",
            name=op.f("ck_tenant_subscriptions_plan_code_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'past_due', 'canceled', 'suspended')",
            name=op.f("ck_tenant_subscriptions_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_tenant_subscriptions_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenant_subscriptions")),
        sa.UniqueConstraint(
            "tenant_id",
            name="tenant_subscription_tenant_id",
        ),
    )
    op.create_index(
        "ix_tenant_subscriptions_status",
        "tenant_subscriptions",
        ["status"],
        unique=False,
    )

    # Existing tenants are placed on the safe baseline plan. A billing provider
    # can later synchronize an authoritative plan/status via the application use case.
    op.execute(
        sa.text(
            """
            INSERT INTO tenant_subscriptions (tenant_id, plan_code, status)
            SELECT id, 'starter'::saas_plan_code, 'active'::saas_subscription_status
            FROM tenants
            ON CONFLICT (tenant_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tenant_subscriptions_status",
        table_name="tenant_subscriptions",
    )
    op.drop_table("tenant_subscriptions")

    bind = op.get_bind()
    postgresql.ENUM(name="saas_subscription_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="saas_plan_code").drop(bind, checkfirst=True)
