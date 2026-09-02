from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.domain.rag_models import DocumentChunk, EmbeddedChunk
from app.ai.infrastructure.vector_store.models import RagChunkModel
from app.ai.infrastructure.vector_store.postgres_vector_store import (
    PostgresVectorStore,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_vector_store_returns_closest_chunk(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid4()
    document_id = "document-1"

    store = PostgresVectorStore(
        session=db_session,
    )

    chunks = (
        EmbeddedChunk(
            chunk=DocumentChunk(
                id=f"{tenant_id}:{document_id}:0",
                document_id=document_id,
                content="Shipment tracking information",
                chunk_index=0,
            ),
            embedding=(1.0,) + (0.0,) * 767,
        ),
        EmbeddedChunk(
            chunk=DocumentChunk(
                id=f"{tenant_id}:{document_id}:1",
                document_id=document_id,
                content="Invoice payment information",
                chunk_index=1,
            ),
            embedding=(0.0, 1.0) + (0.0,) * 766,
        ),
    )

    await store.replace_document(
        tenant_id=tenant_id,
        document_id=document_id,
        chunks=chunks,
    )

    results = await store.search(
        tenant_id=tenant_id,
        query_embedding=(1.0,) + (0.0,) * 767,
        limit=2,
    )

    assert len(results) == 2

    assert results[0].chunk.id == f"{tenant_id}:{document_id}:0"
    assert results[0].chunk.content == "Shipment tracking information"

    assert results[0].score > results[1].score


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_vector_store_isolates_tenants(
    db_session: AsyncSession,
) -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()

    store = PostgresVectorStore(
        session=db_session,
    )

    await store.replace_document(
        tenant_id=tenant_a,
        document_id="document-a",
        chunks=(
            EmbeddedChunk(
                chunk=DocumentChunk(
                    id=f"{tenant_a}:document-a:0",
                    document_id="document-a",
                    content="Tenant A shipment",
                    chunk_index=0,
                ),
                embedding=(1.0,) + (0.0,) * 767,
            ),
        ),
    )

    await store.replace_document(
        tenant_id=tenant_b,
        document_id="document-b",
        chunks=(
            EmbeddedChunk(
                chunk=DocumentChunk(
                    id=f"{tenant_b}:document-b:0",
                    document_id="document-b",
                    content="Tenant B shipment",
                    chunk_index=0,
                ),
                embedding=(1.0,) + (0.0,) * 767,
            ),
        ),
    )

    results = await store.search(
        tenant_id=tenant_a,
        query_embedding=(1.0,) + (0.0,) * 767,
        limit=10,
    )

    assert len(results) == 1

    assert results[0].chunk.document_id == "document-a"
    assert results[0].chunk.content == "Tenant A shipment"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_vector_store_replaces_existing_document_chunks(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid4()
    document_id = "document-reindex"

    store = PostgresVectorStore(
        session=db_session,
    )

    original_chunks = (
        EmbeddedChunk(
            chunk=DocumentChunk(
                id=f"{tenant_id}:{document_id}:0",
                document_id=document_id,
                content="Original chunk zero",
                chunk_index=0,
            ),
            embedding=(1.0,) + (0.0,) * 767,
        ),
        EmbeddedChunk(
            chunk=DocumentChunk(
                id=f"{tenant_id}:{document_id}:1",
                document_id=document_id,
                content="Original chunk one",
                chunk_index=1,
            ),
            embedding=(0.0, 1.0) + (0.0,) * 766,
        ),
        EmbeddedChunk(
            chunk=DocumentChunk(
                id=f"{tenant_id}:{document_id}:2",
                document_id=document_id,
                content="Original stale chunk two",
                chunk_index=2,
            ),
            embedding=(0.0, 0.0, 1.0) + (0.0,) * 765,
        ),
    )

    await store.replace_document(
        tenant_id=tenant_id,
        document_id=document_id,
        chunks=original_chunks,
    )

    replacement_chunks = (
        EmbeddedChunk(
            chunk=DocumentChunk(
                id=f"{tenant_id}:{document_id}:0",
                document_id=document_id,
                content="Updated chunk zero",
                chunk_index=0,
            ),
            embedding=(1.0,) + (0.0,) * 767,
        ),
    )

    await store.replace_document(
        tenant_id=tenant_id,
        document_id=document_id,
        chunks=replacement_chunks,
    )

    result = await db_session.execute(
        select(RagChunkModel)
        .where(
            RagChunkModel.tenant_id == tenant_id,
            RagChunkModel.document_id == document_id,
        )
        .order_by(RagChunkModel.chunk_index)
    )

    stored_chunks = tuple(result.scalars().all())

    assert len(stored_chunks) == 1

    stored_chunk = stored_chunks[0]

    assert stored_chunk.chunk_index == 0
    assert stored_chunk.content == "Updated chunk zero"
    assert stored_chunk.id == f"{tenant_id}:{document_id}:0"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_vector_store_clears_document_when_replaced_with_no_chunks(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid4()
    document_id = "document-cleared"

    store = PostgresVectorStore(session=db_session)

    original_chunks = (
        EmbeddedChunk(
            chunk=DocumentChunk(
                id=f"{tenant_id}:{document_id}:0",
                document_id=document_id,
                content="Old shipment information",
                chunk_index=0,
            ),
            embedding=(1.0,) + (0.0,) * 767,
        ),
        EmbeddedChunk(
            chunk=DocumentChunk(
                id=f"{tenant_id}:{document_id}:1",
                document_id=document_id,
                content="Old customs information",
                chunk_index=1,
            ),
            embedding=(0.0, 1.0) + (0.0,) * 766,
        ),
    )

    await store.replace_document(
        tenant_id=tenant_id,
        document_id=document_id,
        chunks=original_chunks,
    )

    await store.replace_document(
        tenant_id=tenant_id,
        document_id=document_id,
        chunks=(),
    )

    result = await db_session.execute(
        select(RagChunkModel).where(
            RagChunkModel.tenant_id == tenant_id,
            RagChunkModel.document_id == document_id,
        )
    )

    stored_chunks = tuple(result.scalars().all())

    assert stored_chunks == ()
