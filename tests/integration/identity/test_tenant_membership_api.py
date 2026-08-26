from uuid import uuid4

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


async def cleanup_identity_data(
    *,
    email: str,
    tenant_slug: str,
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
            user_id = await session.scalar(select(User.id).where(User.email == email))

            tenant_id = await session.scalar(select(Tenant.id).where(Tenant.slug == tenant_slug))

            if user_id is not None:
                await session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))

            if user_id is not None or tenant_id is not None:
                membership_conditions = []

                if user_id is not None:
                    membership_conditions.append(Membership.user_id == user_id)

                if tenant_id is not None:
                    membership_conditions.append(Membership.tenant_id == tenant_id)

                if membership_conditions:
                    await session.execute(delete(Membership).where(*membership_conditions))

            if user_id is not None:
                await session.execute(delete(User).where(User.id == user_id))

            if tenant_id is not None:
                await session.execute(delete(Tenant).where(Tenant.id == tenant_id))

            await session.commit()
    finally:
        await engine.dispose()


async def create_identity_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    tenant_status: TenantStatus = TenantStatus.ACTIVE,
    membership_status: MembershipStatus = MembershipStatus.ACTIVE,
    create_membership: bool = True,
) -> tuple[User, Tenant]:
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
                first_name="Tenant",
                last_name="User",
                is_active=True,
            )

            tenant = Tenant(
                name="Tenant Integration",
                slug=tenant_slug,
                status=tenant_status,
            )

            role = Role(
                name=f"role-{uuid4()}",
                description="Integration test role",
            )

            session.add_all(
                [
                    user,
                    tenant,
                    role,
                ]
            )

            await session.flush()

            if create_membership:
                session.add(
                    Membership(
                        tenant_id=tenant.id,
                        user_id=user.id,
                        role_id=role.id,
                        status=membership_status,
                    )
                )

            await session.commit()

            return user, tenant
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


@pytest.mark.integration
async def test_tenant_membership_endpoint_returns_membership() -> None:
    email = f"tenant-member-{uuid4()}@example.com"
    password = "very-secure-tenant-password"
    tenant_slug = f"tenant-{uuid4()}"

    await create_identity_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
    )

    try:
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
                tenant_id = await session.scalar(
                    select(Tenant.id).where(Tenant.slug == tenant_slug)
                )
        finally:
            await engine.dispose()

        assert tenant_id is not None

        access_token = await login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant_id}/membership",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["tenant_id"] == str(tenant_id)
        assert body["status"] == MembershipStatus.ACTIVE.value

    finally:
        await cleanup_identity_data(
            email=email,
            tenant_slug=tenant_slug,
        )


@pytest.mark.integration
def test_tenant_membership_endpoint_requires_authentication() -> None:
    response_tenant_id = uuid4()

    with TestClient(app) as client:
        response = client.get(f"/api/v1/tenants/{response_tenant_id}/membership")

    assert response.status_code == 401


@pytest.mark.integration
async def test_tenant_membership_endpoint_rejects_non_member() -> None:
    email = f"tenant-non-member-{uuid4()}@example.com"
    password = "very-secure-tenant-password"
    tenant_slug = f"tenant-{uuid4()}"

    _, tenant = await create_identity_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        create_membership=False,
    )

    try:
        access_token = await login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/membership",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 403
        assert response.json() == {"detail": "Access to this tenant is forbidden"}

    finally:
        await cleanup_identity_data(
            email=email,
            tenant_slug=tenant_slug,
        )


@pytest.mark.integration
async def test_tenant_membership_endpoint_rejects_suspended_membership() -> None:
    email = f"suspended-member-{uuid4()}@example.com"
    password = "very-secure-tenant-password"
    tenant_slug = f"tenant-{uuid4()}"

    _, tenant = await create_identity_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        membership_status=MembershipStatus.SUSPENDED,
    )

    try:
        access_token = await login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/membership",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 403

    finally:
        await cleanup_identity_data(
            email=email,
            tenant_slug=tenant_slug,
        )


@pytest.mark.integration
async def test_tenant_membership_endpoint_rejects_suspended_tenant() -> None:
    email = f"suspended-tenant-{uuid4()}@example.com"
    password = "very-secure-tenant-password"
    tenant_slug = f"tenant-{uuid4()}"

    _, tenant = await create_identity_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        tenant_status=TenantStatus.SUSPENDED,
    )

    try:
        access_token = await login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/membership",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 403

    finally:
        await cleanup_identity_data(
            email=email,
            tenant_slug=tenant_slug,
        )
