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
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.permission import Permission
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.role_permission import RolePermission
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)


async def cleanup_test_data(
    *,
    emails: list[str],
    tenant_slug: str,
    role_names: list[str],
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
            user_ids = list(
                (await session.execute(select(User.id).where(User.email.in_(emails)))).scalars()
            )

            tenant_id = await session.scalar(select(Tenant.id).where(Tenant.slug == tenant_slug))

            role_ids = list(
                (await session.execute(select(Role.id).where(Role.name.in_(role_names)))).scalars()
            )

            if user_ids:
                await session.execute(delete(AuthSession).where(AuthSession.user_id.in_(user_ids)))

                await session.execute(delete(Membership).where(Membership.user_id.in_(user_ids)))

            if tenant_id is not None:
                await session.execute(delete(Membership).where(Membership.tenant_id == tenant_id))

            if role_ids:
                await session.execute(
                    delete(RolePermission).where(RolePermission.role_id.in_(role_ids))
                )

            if user_ids:
                await session.execute(delete(User).where(User.id.in_(user_ids)))

            if tenant_id is not None:
                await session.execute(delete(Tenant).where(Tenant.id == tenant_id))

            if role_ids:
                await session.execute(delete(Role).where(Role.id.in_(role_ids)))

            await session.commit()

    finally:
        await engine.dispose()


async def create_change_role_context(
    *,
    manager_email: str,
    manager_password: str,
    member_email: str,
    tenant_slug: str,
    manager_role_name: str,
    old_role_name: str,
    new_role_name: str,
    grant_membership_manage: bool,
) -> tuple[Tenant, Membership, Role]:
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
            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.MEMBERSHIP_MANAGE)
            )

            assert permission is not None

            manager = User(
                email=manager_email,
                password_hash=password_hasher.hash(manager_password),
                first_name="Role",
                last_name="Manager",
                is_active=True,
            )

            member = User(
                email=member_email,
                password_hash="unused-password-hash",
                first_name="Role",
                last_name="Member",
                is_active=True,
            )

            tenant = Tenant(
                name="Role Change Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            manager_role = Role(
                name=manager_role_name,
                description="Role change manager",
            )

            old_role = Role(
                name=old_role_name,
                description="Old member role",
            )

            new_role = Role(
                name=new_role_name,
                description="New member role",
            )

            session.add_all(
                [
                    manager,
                    member,
                    tenant,
                    manager_role,
                    old_role,
                    new_role,
                ]
            )

            await session.flush()

            manager_membership = Membership(
                tenant_id=tenant.id,
                user_id=manager.id,
                role_id=manager_role.id,
                status=MembershipStatus.ACTIVE,
            )

            member_membership = Membership(
                tenant_id=tenant.id,
                user_id=member.id,
                role_id=old_role.id,
                status=MembershipStatus.ACTIVE,
            )

            session.add_all(
                [
                    manager_membership,
                    member_membership,
                ]
            )

            if grant_membership_manage:
                session.add(
                    RolePermission(
                        role_id=manager_role.id,
                        permission_id=permission.id,
                    )
                )

            await session.commit()

            return tenant, member_membership, new_role

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
async def test_change_member_role_endpoint_updates_role() -> None:
    unique = uuid4()

    manager_email = f"role-manager-{unique}@example.com"
    member_email = f"role-member-{unique}@example.com"
    password = "very-secure-role-password"

    tenant_slug = f"role-tenant-{unique}"

    manager_role_name = f"role-manager-{unique}"
    old_role_name = f"role-old-{unique}"
    new_role_name = f"role-new-{unique}"

    tenant, membership, new_role = await create_change_role_context(
        manager_email=manager_email,
        manager_password=password,
        member_email=member_email,
        tenant_slug=tenant_slug,
        manager_role_name=manager_role_name,
        old_role_name=old_role_name,
        new_role_name=new_role_name,
        grant_membership_manage=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=manager_email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/tenants/{tenant.id}/members/{membership.id}/role",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "role_id": str(new_role.id),
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(membership.id)
        assert body["tenant_id"] == str(tenant.id)
        assert body["role_id"] == str(new_role.id)
        assert body["status"] == "active"

    finally:
        await cleanup_test_data(
            emails=[
                manager_email,
                member_email,
            ],
            tenant_slug=tenant_slug,
            role_names=[
                manager_role_name,
                old_role_name,
                new_role_name,
            ],
        )


@pytest.mark.integration
async def test_change_member_role_endpoint_requires_permission() -> None:
    unique = uuid4()

    manager_email = f"role-denied-{unique}@example.com"
    member_email = f"role-member-{unique}@example.com"
    password = "very-secure-role-password"

    tenant_slug = f"role-denied-tenant-{unique}"

    manager_role_name = f"role-denied-manager-{unique}"
    old_role_name = f"role-denied-old-{unique}"
    new_role_name = f"role-denied-new-{unique}"

    tenant, membership, new_role = await create_change_role_context(
        manager_email=manager_email,
        manager_password=password,
        member_email=member_email,
        tenant_slug=tenant_slug,
        manager_role_name=manager_role_name,
        old_role_name=old_role_name,
        new_role_name=new_role_name,
        grant_membership_manage=False,
    )

    try:
        access_token = login_and_get_access_token(
            email=manager_email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/tenants/{tenant.id}/members/{membership.id}/role",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "role_id": str(new_role.id),
                },
            )

        assert response.status_code == 403
        assert response.json() == {"detail": "Permission denied"}

    finally:
        await cleanup_test_data(
            emails=[
                manager_email,
                member_email,
            ],
            tenant_slug=tenant_slug,
            role_names=[
                manager_role_name,
                old_role_name,
                new_role_name,
            ],
        )


@pytest.mark.integration
async def test_change_member_role_endpoint_rejects_unknown_role() -> None:
    unique = uuid4()

    manager_email = f"role-unknown-{unique}@example.com"
    member_email = f"role-member-{unique}@example.com"
    password = "very-secure-role-password"

    tenant_slug = f"role-unknown-tenant-{unique}"

    manager_role_name = f"role-unknown-manager-{unique}"
    old_role_name = f"role-unknown-old-{unique}"
    new_role_name = f"role-unused-{unique}"

    tenant, membership, _ = await create_change_role_context(
        manager_email=manager_email,
        manager_password=password,
        member_email=member_email,
        tenant_slug=tenant_slug,
        manager_role_name=manager_role_name,
        old_role_name=old_role_name,
        new_role_name=new_role_name,
        grant_membership_manage=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=manager_email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/tenants/{tenant.id}/members/{membership.id}/role",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "role_id": str(uuid4()),
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Role not found"}

    finally:
        await cleanup_test_data(
            emails=[
                manager_email,
                member_email,
            ],
            tenant_slug=tenant_slug,
            role_names=[
                manager_role_name,
                old_role_name,
                new_role_name,
            ],
        )
