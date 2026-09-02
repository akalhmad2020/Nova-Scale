from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.ai.application.services.chunk_text import ChunkTextService
from app.ai.application.services.embed_document import EmbedDocumentService
from app.ai.application.services.ingest_document import IngestDocumentService
from app.ai.infrastructure.dependencies import build_embedding_provider
from app.ai.infrastructure.vector_store.models import RagChunkModel
from app.ai.infrastructure.vector_store.postgres_vector_store import (
    PostgresVectorStore,
)
from app.core.config import get_settings
from app.main import app
from app.modules.identity.domain.enums import MembershipStatus, TenantStatus
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)


async def create_identity_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
) -> Tenant:
    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    password_hasher = Argon2PasswordHasher()

    try:
        async with session_factory() as session:
            user = User(
                email=email,
                password_hash=password_hasher.hash(password),
                first_name="RAG",
                last_name="User",
                is_active=True,
            )

            tenant = Tenant(
                name="RAG Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=f"rag-role-{uuid4()}",
                description="RAG integration test role",
            )

            session.add_all(
                [
                    user,
                    tenant,
                    role,
                ]
            )

            await session.flush()

            session.add(
                Membership(
                    tenant_id=tenant.id,
                    user_id=user.id,
                    role_id=role.id,
                    status=MembershipStatus.ACTIVE,
                )
            )

            await session.commit()

            return tenant
    finally:
        await engine.dispose()


async def create_tenant_without_membership(
    *,
    tenant_slug: str,
) -> Tenant:
    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    try:
        async with session_factory() as session:
            tenant = Tenant(
                name="Other RAG Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)

            await session.commit()

            return tenant
    finally:
        await engine.dispose()


async def login_and_get_access_token(
    *,
    email: str,
    password: str,
) -> str:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

    assert response.status_code == 200

    access_token = response.json()["access_token"]

    assert isinstance(access_token, str)

    return access_token


async def ingest_test_document(
    *,
    tenant_id: UUID,
    document_id: str,
    text: str,
) -> None:
    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    try:
        async with session_factory() as session:
            embedding_provider = build_embedding_provider(settings)

            vector_store = PostgresVectorStore(
                session=session,
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

            chunk_count = await ingest_document_service.execute(
                tenant_id=tenant_id,
                document_id=document_id,
                text=text,
            )

            assert chunk_count > 0

            await session.commit()
    finally:
        await engine.dispose()


async def cleanup_test_data(
    *,
    email: str,
    tenant_ids: tuple[UUID, ...],
) -> None:
    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    try:
        async with session_factory() as session:
            user_id = await session.scalar(
                select(User.id).where(
                    User.email == email,
                )
            )

            await session.execute(
                delete(RagChunkModel).where(
                    RagChunkModel.tenant_id.in_(tenant_ids),
                )
            )

            if user_id is not None:
                await session.execute(
                    delete(AuthSession).where(
                        AuthSession.user_id == user_id,
                    )
                )

                await session.execute(
                    delete(Membership).where(
                        Membership.user_id == user_id,
                    )
                )

                await session.execute(
                    delete(User).where(
                        User.id == user_id,
                    )
                )

            await session.execute(
                delete(Membership).where(
                    Membership.tenant_id.in_(tenant_ids),
                )
            )

            await session.execute(
                delete(Tenant).where(
                    Tenant.id.in_(tenant_ids),
                )
            )

            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.integration
@pytest.mark.external_ai
async def test_ask_question_endpoint_runs_authenticated_rag_pipeline() -> None:
    email = f"rag-api-{uuid4()}@example.com"
    password = "very-secure-rag-password"
    tenant_slug = f"rag-tenant-{uuid4()}"

    tenant = await create_identity_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
    )

    document_id = str(uuid4())

    try:
        await ingest_test_document(
            tenant_id=tenant.id,
            document_id=document_id,
            text=(
                "Shipment NOVA-100 is currently in transit. "
                "The shipment departed the Ramallah distribution center "
                "and is expected to reach its destination tomorrow."
            ),
        )

        access_token = await login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/ai/tenants/{tenant.id}/ask",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "question": "What is the status of shipment NOVA-100?",
                    "limit": 5,
                },
            )

        assert response.status_code == 200

        data = response.json()

        assert data["content"].strip()
        assert data["model"] == get_settings().ai_ollama_model

        assert data["sources"]

        document_ids = {source["document_id"] for source in data["sources"]}

        assert document_id in document_ids

        matching_source = next(
            source for source in data["sources"] if source["document_id"] == document_id
        )

        assert "NOVA-100" in matching_source["content"]

    finally:
        await cleanup_test_data(
            email=email,
            tenant_ids=(tenant.id,),
        )


@pytest.mark.integration
async def test_ask_question_endpoint_rejects_cross_tenant_access() -> None:
    email = f"rag-cross-tenant-{uuid4()}@example.com"
    password = "very-secure-rag-password"

    tenant_a = await create_identity_context(
        email=email,
        password=password,
        tenant_slug=f"rag-tenant-a-{uuid4()}",
    )

    tenant_b = await create_tenant_without_membership(
        tenant_slug=f"rag-tenant-b-{uuid4()}",
    )

    try:
        access_token = await login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/ai/tenants/{tenant_b.id}/ask",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "question": "Show me this tenant's shipment information.",
                    "limit": 5,
                },
            )

        assert response.status_code == 403
        assert response.json() == {"detail": "Access to this tenant is forbidden"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_ids=(
                tenant_a.id,
                tenant_b.id,
            ),
        )


@pytest.mark.integration
def test_ask_question_endpoint_requires_authentication() -> None:
    tenant_id = uuid4()

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/ai/tenants/{tenant_id}/ask",
            json={
                "question": "Where is my shipment?",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
