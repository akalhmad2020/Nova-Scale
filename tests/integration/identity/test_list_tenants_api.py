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
from app.modules.identity.domain.enums import MembershipStatus, TenantStatus
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)


async def cleanup_test_data(
    *,
    email: str,
    tenant_slugs: list[str],
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

            tenant_ids = list(
                (
                    await session.execute(select(Tenant.id).where(Tenant.slug.in_(tenant_slugs)))
                ).scalars()
            )

            if user_id is not None:
                await session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))

                await session.execute(delete(Membership).where(Membership.user_id == user_id))

            if tenant_ids:
                await session.execute(
                    delete(Membership).where(Membership.tenant_id.in_(tenant_ids))
                )

            if user_id is not None:
                await session.execute(delete(User).where(User.id == user_id))

            if tenant_ids:
                await session.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))

            await session.commit()

    finally:
        await engine.dispose()


async def create_test_context(
    *,
    email: str,
    password: str,
    active_tenant_slugs: list[str],
    suspended_tenant_slug: str,
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

    password_hasher = Argon2PasswordHasher()

    try:
        async with session_factory() as session:
            owner_role = await session.scalar(select(Role).where(Role.name == "owner"))

            assert owner_role is not None

            user = User(
                email=email,
                password_hash=password_hasher.hash(password),
                first_name="Tenant",
                last_name="Lister",
                is_active=True,
            )

            session.add(user)
            await session.flush()

            for slug in active_tenant_slugs:
                tenant = Tenant(
                    name=f"Tenant {slug}",
                    slug=slug,
                    status=TenantStatus.ACTIVE,
                )

                session.add(tenant)
                await session.flush()

                session.add(
                    Membership(
                        tenant_id=tenant.id,
                        user_id=user.id,
                        role_id=owner_role.id,
                        status=MembershipStatus.ACTIVE,
                    )
                )

            suspended_tenant = Tenant(
                name="Suspended Membership Tenant",
                slug=suspended_tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(suspended_tenant)
            await session.flush()

            session.add(
                Membership(
                    tenant_id=suspended_tenant.id,
                    user_id=user.id,
                    role_id=owner_role.id,
                    status=MembershipStatus.SUSPENDED,
                )
            )

            await session.commit()

    finally:
        await engine.dispose()


def login_and_get_access_token(
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
async def test_list_tenants_returns_only_active_memberships() -> None:
    unique = uuid4()

    email = f"list-tenants-{unique}@example.com"
    password = "very-secure-tenant-password"

    first_slug = f"tenant-one-{unique}"
    second_slug = f"tenant-two-{unique}"
    suspended_slug = f"tenant-suspended-{unique}"

    await create_test_context(
        email=email,
        password=password,
        active_tenant_slugs=[
            first_slug,
            second_slug,
        ],
        suspended_tenant_slug=suspended_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/tenants",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 2

        returned_slugs = {item["slug"] for item in body}

        assert returned_slugs == {
            first_slug,
            second_slug,
        }

        assert suspended_slug not in returned_slugs

        for item in body:
            assert item["id"]
            assert item["membership_id"]
            assert item["role_id"]
            assert item["name"]
            assert item["slug"]

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=[
                first_slug,
                second_slug,
                suspended_slug,
            ],
        )


@pytest.mark.integration
def test_list_tenants_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/tenants",
        )

    assert response.status_code == 401
