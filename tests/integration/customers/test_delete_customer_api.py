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
from app.modules.customers.domain.enums import CustomerStatus
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


async def create_delete_context(
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
                last_name="Deleter",
                is_active=True,
            )

            tenant = Tenant(
                name="Customer Delete Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Customer delete integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.CUSTOMER_DELETE)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.CUSTOMER_DELETE,
                    description="Delete customers",
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


async def create_customer(
    *,
    tenant_id: UUID,
    name: str,
    code: str,
) -> Customer:
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
            customer = Customer(
                tenant_id=tenant_id,
                name=name,
                code=code,
                status=CustomerStatus.ACTIVE,
            )

            session.add(customer)
            await session.commit()

            return customer

    finally:
        await engine.dispose()


async def get_customer_raw(
    customer_id: UUID,
) -> Customer | None:
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
            customer = await session.get(
                Customer,
                customer_id,
            )

            return customer

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
async def test_delete_customer_endpoint_soft_deletes_customer() -> None:
    unique = uuid4()

    email = f"customer-delete-{unique}@example.com"
    password = "very-secure-customer-password"
    tenant_slug = f"customer-delete-tenant-{unique}"
    role_name = f"customer-delete-role-{unique}"

    tenant = await create_delete_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        customer = await create_customer(
            tenant_id=tenant.id,
            name="Customer To Delete",
            code="DELETE-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.delete(
                f"/api/v1/tenants/{tenant.id}/customers/{customer.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 204
        assert response.content == b""

        stored = await get_customer_raw(customer.id)

        assert stored is not None
        assert stored.deleted_at is not None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_delete_customer_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"customer-delete-denied-{unique}@example.com"
    password = "very-secure-customer-password"
    tenant_slug = f"customer-delete-denied-{unique}"
    role_name = f"customer-delete-denied-role-{unique}"

    tenant = await create_delete_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=False,
    )

    try:
        customer = await create_customer(
            tenant_id=tenant.id,
            name="Protected Customer",
            code="PROTECTED-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.delete(
                f"/api/v1/tenants/{tenant.id}/customers/{customer.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 403
        assert response.json() == {"detail": "Permission denied"}

        stored = await get_customer_raw(customer.id)

        assert stored is not None
        assert stored.deleted_at is None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_delete_customer_endpoint_rejects_unknown_customer() -> None:
    unique = uuid4()

    email = f"customer-delete-missing-{unique}@example.com"
    password = "very-secure-customer-password"
    tenant_slug = f"customer-delete-missing-{unique}"
    role_name = f"customer-delete-missing-role-{unique}"

    tenant = await create_delete_context(
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
            response = client.delete(
                f"/api/v1/tenants/{tenant.id}/customers/{uuid4()}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Customer not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_delete_customer_endpoint_rejects_customer_from_other_tenant() -> None:
    unique = uuid4()

    first_email = f"customer-delete-first-{unique}@example.com"
    second_email = f"customer-delete-second-{unique}@example.com"

    password = "very-secure-customer-password"

    first_slug = f"customer-delete-first-{unique}"
    second_slug = f"customer-delete-second-{unique}"

    first_role = f"customer-delete-first-role-{unique}"
    second_role = f"customer-delete-second-role-{unique}"

    first_tenant = await create_delete_context(
        email=first_email,
        password=password,
        tenant_slug=first_slug,
        role_name=first_role,
        assign_permission=True,
    )

    second_tenant = await create_delete_context(
        email=second_email,
        password=password,
        tenant_slug=second_slug,
        role_name=second_role,
        assign_permission=True,
    )

    try:
        foreign_customer = await create_customer(
            tenant_id=second_tenant.id,
            name="Foreign Customer",
            code="FOREIGN-DELETE-001",
        )

        access_token = login_and_get_access_token(
            email=first_email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.delete(
                f"/api/v1/tenants/{first_tenant.id}/customers/{foreign_customer.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Customer not found"}

        stored = await get_customer_raw(foreign_customer.id)

        assert stored is not None
        assert stored.deleted_at is None

    finally:
        await cleanup_test_data(
            email=first_email,
            tenant_slug=first_slug,
            role_name=first_role,
        )

        await cleanup_test_data(
            email=second_email,
            tenant_slug=second_slug,
            role_name=second_role,
        )
