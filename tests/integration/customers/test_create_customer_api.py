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
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.identity.domain.enums import (
    MembershipStatus,
    TenantStatus,
)
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.permission import Permission
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.role_permission import (
    RolePermission,
)
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)


async def cleanup_test_data(
    *,
    email: str,
    tenant_slug: str,
    role_name: str,
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

            role_id = await session.scalar(select(Role.id).where(Role.name == role_name))

            if tenant_id is not None:
                await session.execute(delete(Customer).where(Customer.tenant_id == tenant_id))

            if user_id is not None:
                await session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))

                await session.execute(delete(Membership).where(Membership.user_id == user_id))

            if tenant_id is not None:
                await session.execute(delete(Membership).where(Membership.tenant_id == tenant_id))

            if role_id is not None:
                await session.execute(
                    delete(RolePermission).where(RolePermission.role_id == role_id)
                )

            if user_id is not None:
                await session.execute(delete(User).where(User.id == user_id))

            if tenant_id is not None:
                await session.execute(delete(Tenant).where(Tenant.id == tenant_id))

            if role_id is not None:
                await session.execute(delete(Role).where(Role.id == role_id))

            await session.commit()

    finally:
        await engine.dispose()


async def create_customer_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
    assign_permission: bool,
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
                first_name="Customer",
                last_name="Manager",
                is_active=True,
            )

            tenant = Tenant(
                name="Customers Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Customers integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.CUSTOMER_CREATE)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.CUSTOMER_CREATE,
                    description="Create customers",
                )
                session.add(permission)

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

            if assign_permission:
                session.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                    )
                )

            await session.commit()

            return tenant

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
async def test_create_customer_endpoint_creates_customer() -> None:
    unique = uuid4()

    email = f"customer-create-{unique}@example.com"
    password = "very-secure-customer-password"
    tenant_slug = f"customer-tenant-{unique}"
    role_name = f"customer-role-{unique}"

    tenant = await create_customer_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/customers",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "  Acme Trading  ",
                    "code": "  acme-001  ",
                    "email": "CONTACT@ACME.EXAMPLE",
                    "phone": "  +970599000000  ",
                    "notes": "  Integration customer  ",
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["name"] == "Acme Trading"
        assert body["code"] == "ACME-001"
        assert body["email"] == "contact@acme.example"
        assert body["phone"] == "+970599000000"
        assert body["notes"] == "Integration customer"
        assert body["status"] == "active"
        assert body["id"]

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_customer_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"customer-denied-{unique}@example.com"
    password = "very-secure-customer-password"
    tenant_slug = f"customer-denied-tenant-{unique}"
    role_name = f"customer-denied-role-{unique}"

    tenant = await create_customer_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=False,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/customers",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "Denied Customer",
                    "code": "DENIED-001",
                },
            )

        assert response.status_code == 403
        assert response.json() == {"detail": "Permission denied"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_customer_endpoint_rejects_duplicate_code() -> None:
    unique = uuid4()

    email = f"customer-duplicate-{unique}@example.com"
    password = "very-secure-customer-password"
    tenant_slug = f"customer-duplicate-tenant-{unique}"
    role_name = f"customer-duplicate-role-{unique}"

    tenant = await create_customer_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            first_response = client.post(
                f"/api/v1/tenants/{tenant.id}/customers",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "First Customer",
                    "code": "CUST-001",
                },
            )

            second_response = client.post(
                f"/api/v1/tenants/{tenant.id}/customers",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "Second Customer",
                    "code": " cust-001 ",
                },
            )

        assert first_response.status_code == 201

        assert second_response.status_code == 409
        assert second_response.json() == {"detail": "Customer code already exists"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )
