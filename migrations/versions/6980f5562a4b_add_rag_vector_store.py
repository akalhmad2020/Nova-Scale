"""add rag vector store

Revision ID: 6980f5562a4b
Revises: 082f86c344fd
Create Date: 2026-09-01 15:35:35.328256
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "6980f5562a4b"
down_revision: str | Sequence[str] | None = "082f86c344fd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "rag_chunks",
        sa.Column(
            "id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "chunk_index",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "embedding",
            Vector(768),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_rag_chunks"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "document_id",
            "chunk_index",
            name=op.f(
                "uq_rag_chunks_tenant_id_document_id_chunk_index"
            ),
        ),
    )

    op.create_index(
        op.f("ix_rag_chunks_tenant_id"),
        "rag_chunks",
        ["tenant_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_rag_chunks_document_id"),
        "rag_chunks",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("rag_chunks")

    op.execute("DROP EXTENSION IF EXISTS vector")