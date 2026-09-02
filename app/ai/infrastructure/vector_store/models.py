from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base


class RagChunkModel(Base):
    __tablename__ = "rag_chunks"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "document_id",
            "chunk_index",
            name="uq_rag_chunks_tenant_id_document_id_chunk_index",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
        index=True,
    )

    document_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(768),
        nullable=False,
    )
