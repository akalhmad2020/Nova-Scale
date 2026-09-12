from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

import app.core.database  # noqa: F401
from app.ai.application.agent.decision import AgentDecision
from app.ai.application.dependencies import build_agent_runtime
from app.ai.application.services.chunk_text import ChunkTextService
from app.ai.application.services.embed_document import EmbedDocumentService
from app.ai.application.services.ingest_document import IngestDocumentService
from app.ai.infrastructure.dependencies import build_embedding_provider
from app.ai.infrastructure.vector_store.postgres_vector_store import (
    PostgresVectorStore,
)
from app.core.config import get_settings
from app.core.tenant_context import (
    reset_current_tenant_id,
    set_current_tenant_id,
)
from app.modules.identity.api.dependencies import (
    get_check_permission_use_case,
)
from app.modules.identity.application.use_cases.check_permission import (
    CheckPermissionQuery,
)
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.permission import Permission
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.role_permission import (
    RolePermission,
)
from tests.unit.ai.fakes import FakeAgentPlanner


async def set_session_tenant_context(
    session: AsyncSession,
    tenant_id: UUID,
) -> None:
    await session.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant_id',
                :tenant_id,
                true
            )
            """
        ),
        {"tenant_id": str(tenant_id)},
    )


async def create_role_with_permission(
    *,
    session: AsyncSession,
    permission_code: str,
) -> UUID:
    permission = await session.scalar(
        select(Permission).where(
            Permission.code == permission_code,
        )
    )

    if permission is None:
        permission = Permission(
            code=permission_code,
            description=f"Integration test permission: {permission_code}",
        )

        session.add(permission)
        await session.flush()

    role = Role(
        name=f"ai-integration-role-{uuid4()}",
        description="AI integration test role",
    )

    session.add(role)
    await session.flush()

    session.add(
        RolePermission(
            role_id=role.id,
            permission_id=permission.id,
        )
    )

    await session.flush()

    return role.id


@pytest.mark.integration
@pytest.mark.external_ai
@pytest.mark.asyncio
async def test_agent_answers_from_real_rag_context(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid4()
    document_id = str(uuid4())

    settings = get_settings()

    role_id = await create_role_with_permission(
        session=db_session,
        permission_code=Permissions.DOCUMENT_READ,
    )

    await db_session.commit()

    check_permission = get_check_permission_use_case()

    await check_permission.execute(
        CheckPermissionQuery(
            role_id=role_id,
            permission_code=Permissions.DOCUMENT_READ,
        )
    )

    embedding_provider = build_embedding_provider(settings)

    vector_store = PostgresVectorStore(
        session=db_session,
    )

    embed_document_service = EmbedDocumentService(
        chunk_text_service=ChunkTextService(
            chunk_size=1000,
            chunk_overlap=150,
        ),
        embedding_provider=embedding_provider,
    )

    ingest_document_service = IngestDocumentService(
        embed_document_service=embed_document_service,
        vector_store=vector_store,
    )

    await set_session_tenant_context(
        db_session,
        tenant_id,
    )

    indexed_chunks = await ingest_document_service.execute(
        tenant_id=tenant_id,
        document_id=document_id,
        text=(
            "NovaScale tenant shipping policy states that damaged cargo "
            "must be reported within 48 hours of delivery. "
            "The report must include the shipment reference and "
            "supporting evidence."
        ),
    )

    assert indexed_chunks > 0

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="retrieve_context",
    )

    runtime._agent_planner = planner

    await set_session_tenant_context(
        db_session,
        tenant_id,
    )

    tenant_context_token = set_current_tenant_id(
        tenant_id,
    )

    question = (
        "According to our tenant shipping documents, "
        "within how many hours must damaged cargo be reported?"
    )

    try:
        answer = await runtime.execute(
            tenant_id=tenant_id,
            role_id=role_id,
            question=question,
        )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert planner.questions == [
        question,
    ]

    assert answer.strip()

    normalized_answer = answer.lower()

    assert "48" in normalized_answer


@pytest.mark.integration
@pytest.mark.external_ai
@pytest.mark.asyncio
async def test_agent_rag_cannot_retrieve_context_from_another_tenant(
    db_session: AsyncSession,
) -> None:
    owner_tenant_id = uuid4()
    foreign_tenant_id = uuid4()
    document_id = str(uuid4())

    settings = get_settings()

    role_id = await create_role_with_permission(
        session=db_session,
        permission_code=Permissions.DOCUMENT_READ,
    )

    embedding_provider = build_embedding_provider(settings)

    vector_store = PostgresVectorStore(
        session=db_session,
    )

    embed_document_service = EmbedDocumentService(
        chunk_text_service=ChunkTextService(
            chunk_size=1000,
            chunk_overlap=150,
        ),
        embedding_provider=embedding_provider,
    )

    ingest_document_service = IngestDocumentService(
        embed_document_service=embed_document_service,
        vector_store=vector_store,
    )

    await set_session_tenant_context(
        db_session,
        owner_tenant_id,
    )

    indexed_chunks = await ingest_document_service.execute(
        tenant_id=owner_tenant_id,
        document_id=document_id,
        text=(
            "NovaScale confidential tenant policy states that "
            "damaged cargo must be reported within 72 hours."
        ),
    )

    assert indexed_chunks > 0

    runtime = build_agent_runtime(
        settings=settings,
        session=db_session,
    )

    planner = FakeAgentPlanner()
    planner.decision = AgentDecision(
        route="retrieve_context",
    )

    runtime._agent_planner = planner

    await set_session_tenant_context(
        db_session,
        foreign_tenant_id,
    )

    tenant_context_token = set_current_tenant_id(
        foreign_tenant_id,
    )

    question = (
        "According to our tenant documents, within how many hours must damaged cargo be reported?"
    )

    try:
        answer = await runtime.execute(
            tenant_id=foreign_tenant_id,
            role_id=role_id,
            question=question,
        )
    finally:
        reset_current_tenant_id(
            tenant_context_token,
        )

    assert planner.questions == [
        question,
    ]

    assert answer.strip()

    normalized_answer = answer.lower()

    assert "72" not in normalized_answer
