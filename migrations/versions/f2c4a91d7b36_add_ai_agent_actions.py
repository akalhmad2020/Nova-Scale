"""add ai agent actions

Revision ID: f2c4a91d7b36
Revises: a31c7d8e5f20
Create Date: 2026-09-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2c4a91d7b36"
down_revision: str | None = "a31c7d8e5f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_agent_actions",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "idempotency_key",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=40),
            nullable=False,
            server_default="pending_confirmation",
        ),
        sa.Column(
            "resource_type",
            sa.String(length=100),
            nullable=False,
            server_default="shipment",
        ),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "shipment_identifier",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column("expected_status", sa.String(length=50), nullable=False),
        sa.Column("target_status", sa.String(length=50), nullable=True),
        sa.Column("expected_notes", sa.Text(), nullable=True),
        sa.Column("new_notes", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
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
            "action_type IN ('transition_shipment_status', 'update_shipment_notes')",
            name="ck_ai_agent_actions_action_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending_confirmation', 'executing', 'executed', "
            "'cancelled', 'failed')",
            name="ck_ai_agent_actions_status",
        ),
        sa.CheckConstraint(
            "resource_type = 'shipment'",
            name="ck_ai_agent_actions_resource_type",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_ai_agent_actions_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_ai_agent_actions_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["ai_conversations.id"],
            name="fk_ai_agent_actions_conversation_id_ai_conversations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_agent_actions"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_ai_agent_actions_idempotency_key",
        ),
    )

    op.create_index(
        "ix_ai_agent_actions_tenant_user_created_at",
        "ai_agent_actions",
        ["tenant_id", "user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ai_agent_actions_conversation_created_at",
        "ai_agent_actions",
        ["conversation_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_ai_agent_actions_active_conversation",
        "ai_agent_actions",
        ["conversation_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('pending_confirmation', 'executing')"
        ),
    )

    op.execute("ALTER TABLE ai_agent_actions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_agent_actions FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY ai_agent_actions_tenant_isolation
        ON ai_agent_actions
        USING (
            tenant_id = NULLIF(
                current_setting('app.current_tenant_id', true),
                ''
            )::uuid
        )
        WITH CHECK (
            tenant_id = NULLIF(
                current_setting('app.current_tenant_id', true),
                ''
            )::uuid
        )
        """
    )


def downgrade() -> None:
    op.drop_table("ai_agent_actions")
