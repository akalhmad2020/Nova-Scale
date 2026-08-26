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
    emails: list[str],
    tenant_slugs: list[str],
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

            tenant_ids = list(
                (
                    await session.execute(select(Tenant.id).where(Tenant.slug.in_(tenant_slugs)))
                ).scalars()
            )

            role_ids = list(
                (await session.execute(select(Role.id).where(Role.name.in_(role_names)))).scalars()
            )

            if user_ids:
                await session.execute(delete(AuthSession).where(AuthSession.user_id.in_(user_ids)))

                await session.execute(delete(Membership).where(Membership.user_id.in_(user_ids)))

            if tenant_ids:
                await session.execute(
                    delete(Membership).where(Membership.tenant_id.in_(tenant_ids))
                )

            if role_ids:
                await session.execute(
                    delete(RolePermission).where(RolePermission.role_id.in_(role_ids))
                )

            if user_ids:
                await session.execute(delete(User).where(User.id.in_(user_ids)))

            if tenant_ids:
                await session.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))

            if role_ids:
                await session.execute(delete(Role).where(Role.id.in_(role_ids)))

            await session.commit()

    finally:
        await engine.dispose()


async def create_tenant_member_context(
    *,
    manager_email: str,
    manager_password: str,
    member_email: str,
    tenant_slug: str,
    manager_role_name: str,
    member_role_name: str,
    grant_membership_read: bool,
) -> tuple[Tenant, User, User, Role]:
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
                select(Permission).where(Permission.code == Permissions.MEMBERSHIP_READ)
            )

            assert permission is not None

            manager = User(
                email=manager_email,
                password_hash=password_hasher.hash(manager_password),
                first_name="Tenant",
                last_name="Manager",
                is_active=True,
            )

            member = User(
                email=member_email,
                password_hash="unused-password-hash",
                first_name="Tenant",
                last_name="Member",
                is_active=True,
            )

            tenant = Tenant(
                name="Members Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            manager_role = Role(
                name=manager_role_name,
                description="Members integration manager role",
            )

            member_role = Role(
                name=member_role_name,
                description="Members integration member role",
            )

            session.add_all(
                [
                    manager,
                    member,
                    tenant,
                    manager_role,
                    member_role,
                ]
            )

            await session.flush()

            session.add_all(
                [
                    Membership(
                        tenant_id=tenant.id,
                        user_id=manager.id,
                        role_id=manager_role.id,
                        status=MembershipStatus.ACTIVE,
                    ),
                    Membership(
                        tenant_id=tenant.id,
                        user_id=member.id,
                        role_id=member_role.id,
                        status=MembershipStatus.ACTIVE,
                    ),
                ]
            )

            if grant_membership_read:
                session.add(
                    RolePermission(
                        role_id=manager_role.id,
                        permission_id=permission.id,
                    )
                )

            await session.commit()

            return (
                tenant,
                manager,
                member,
                member_role,
            )

    finally:
        await engine.dispose()


async def create_foreign_tenant_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
) -> tuple[Tenant, User]:
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
                select(Permission).where(Permission.code == Permissions.MEMBERSHIP_READ)
            )

            assert permission is not None

            user = User(
                email=email,
                password_hash=password_hasher.hash(password),
                first_name="Foreign",
                last_name="Manager",
                is_active=True,
            )

            tenant = Tenant(
                name="Foreign Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Foreign tenant manager role",
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

            session.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                )
            )

            await session.commit()

            return tenant, user

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
async def test_list_tenant_members_returns_active_members() -> None:
    unique = uuid4()

    manager_email = f"members-manager-{unique}@example.com"
    member_email = f"members-user-{unique}@example.com"
    password = "very-secure-members-password"

    tenant_slug = f"members-tenant-{unique}"
    manager_role_name = f"members-manager-role-{unique}"
    member_role_name = f"members-member-role-{unique}"

    tenant, manager, member, member_role = await create_tenant_member_context(
        manager_email=manager_email,
        manager_password=password,
        member_email=member_email,
        tenant_slug=tenant_slug,
        manager_role_name=manager_role_name,
        member_role_name=member_role_name,
        grant_membership_read=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=manager_email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/members",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 2

        returned_user_ids = {item["user_id"] for item in body}

        assert returned_user_ids == {
            str(manager.id),
            str(member.id),
        }

        member_response = next(item for item in body if item["user_id"] == str(member.id))

        assert member_response["email"] == member_email
        assert member_response["first_name"] == "Tenant"
        assert member_response["last_name"] == "Member"
        assert member_response["role_id"] == str(member_role.id)
        assert member_response["membership_id"]

    finally:
        await cleanup_test_data(
            emails=[
                manager_email,
                member_email,
            ],
            tenant_slugs=[tenant_slug],
            role_names=[
                manager_role_name,
                member_role_name,
            ],
        )


@pytest.mark.integration
async def test_list_tenant_members_requires_permission() -> None:
    unique = uuid4()

    manager_email = f"members-denied-{unique}@example.com"
    member_email = f"members-user-{unique}@example.com"
    password = "very-secure-members-password"

    tenant_slug = f"members-denied-tenant-{unique}"
    manager_role_name = f"members-denied-role-{unique}"
    member_role_name = f"members-member-role-{unique}"

    tenant, _, _, _ = await create_tenant_member_context(
        manager_email=manager_email,
        manager_password=password,
        member_email=member_email,
        tenant_slug=tenant_slug,
        manager_role_name=manager_role_name,
        member_role_name=member_role_name,
        grant_membership_read=False,
    )

    try:
        access_token = login_and_get_access_token(
            email=manager_email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/members",
                headers={
                    "Authorization": f"Bearer {access_token}",
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
            tenant_slugs=[tenant_slug],
            role_names=[
                manager_role_name,
                member_role_name,
            ],
        )


@pytest.mark.integration
async def test_list_tenant_members_rejects_user_from_other_tenant() -> None:
    unique = uuid4()

    target_manager_email = f"target-manager-{unique}@example.com"
    target_member_email = f"target-member-{unique}@example.com"

    foreign_email = f"foreign-manager-{unique}@example.com"

    password = "very-secure-members-password"

    target_slug = f"target-tenant-{unique}"
    foreign_slug = f"foreign-tenant-{unique}"

    target_manager_role = f"target-manager-role-{unique}"
    target_member_role = f"target-member-role-{unique}"
    foreign_role = f"foreign-role-{unique}"

    target_tenant, _, _, _ = await create_tenant_member_context(
        manager_email=target_manager_email,
        manager_password=password,
        member_email=target_member_email,
        tenant_slug=target_slug,
        manager_role_name=target_manager_role,
        member_role_name=target_member_role,
        grant_membership_read=True,
    )

    await create_foreign_tenant_context(
        email=foreign_email,
        password=password,
        tenant_slug=foreign_slug,
        role_name=foreign_role,
    )

    try:
        access_token = login_and_get_access_token(
            email=foreign_email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{target_tenant.id}/members",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code in {
            403,
            404,
        }

    finally:
        await cleanup_test_data(
            emails=[
                target_manager_email,
                target_member_email,
                foreign_email,
            ],
            tenant_slugs=[
                target_slug,
                foreign_slug,
            ],
            role_names=[
                target_manager_role,
                target_member_role,
                foreign_role,
            ],
        )
