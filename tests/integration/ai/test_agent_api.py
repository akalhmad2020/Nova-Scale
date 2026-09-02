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

from app.core.config import get_settings
from app.main import app
from app.modules.identity.domain.enums import (
    MembershipStatus,
    TenantStatus,
)
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
                first_name="Agent",
                last_name="User",
                is_active=True,
            )

            tenant = Tenant(
                name="Agent API Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=f"agent-api-role-{uuid4()}",
                description="Agent API integration test role",
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
                name="Other Agent Tenant",
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
@pytest.mark.asyncio
async def test_agent_endpoint_rejects_cross_tenant_access() -> None:
    email = f"agent-cross-tenant-{uuid4()}@example.com"
    password = "very-secure-agent-password"

    tenant_a = await create_identity_context(
        email=email,
        password=password,
        tenant_slug=f"agent-tenant-a-{uuid4()}",
    )

    tenant_b = await create_tenant_without_membership(
        tenant_slug=f"agent-tenant-b-{uuid4()}",
    )

    try:
        access_token = await login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/ai/tenants/{tenant_b.id}/agent",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "question": "Tell me about this tenant.",
                },
            )

        assert response.status_code == 403
        assert response.json() == {
            "detail": "Access to this tenant is forbidden",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_ids=(
                tenant_a.id,
                tenant_b.id,
            ),
        )


@pytest.mark.integration
def test_agent_endpoint_requires_authentication() -> None:
    tenant_id = uuid4()

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/ai/tenants/{tenant_id}/agent",
            json={
                "question": "Where is my shipment?",
            },
        )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required",
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_endpoint_runs_authenticated_agent() -> None:
    email = f"agent-api-{uuid4()}@example.com"
    password = "very-secure-agent-password"

    tenant = await create_identity_context(
        email=email,
        password=password,
        tenant_slug=f"agent-tenant-{uuid4()}",
    )

    try:
        access_token = await login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/ai/tenants/{tenant.id}/agent",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "question": (
                        "Briefly explain what a shipment tracking number is. "
                        "Do not look up a specific shipment."
                    ),
                },
            )

        assert response.status_code == 200

        data = response.json()

        assert isinstance(data["answer"], str)
        assert data["answer"].strip()

    finally:
        await cleanup_test_data(
            email=email,
            tenant_ids=(tenant.id,),
        )
