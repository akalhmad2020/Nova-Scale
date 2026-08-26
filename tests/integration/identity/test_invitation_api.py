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
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.invitation import Invitation
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
                await session.execute(delete(Invitation).where(Invitation.tenant_id == tenant_id))

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


async def create_invitation_context(
    *,
    inviter_email: str,
    inviter_password: str,
    tenant_slug: str,
    inviter_role_name: str,
    invited_role_name: str,
    grant_membership_manage: bool,
) -> tuple[Tenant, Role]:
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

            inviter = User(
                email=inviter_email,
                password_hash=password_hasher.hash(inviter_password),
                first_name="Invitation",
                last_name="Manager",
                is_active=True,
            )

            tenant = Tenant(
                name="Invitation Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            inviter_role = Role(
                name=inviter_role_name,
                description="Invitation test inviter role",
            )

            invited_role = Role(
                name=invited_role_name,
                description="Invitation target role",
            )

            session.add_all(
                [
                    inviter,
                    tenant,
                    inviter_role,
                    invited_role,
                ]
            )

            await session.flush()

            session.add(
                Membership(
                    tenant_id=tenant.id,
                    user_id=inviter.id,
                    role_id=inviter_role.id,
                    status=MembershipStatus.ACTIVE,
                )
            )

            if grant_membership_manage:
                session.add(
                    RolePermission(
                        role_id=inviter_role.id,
                        permission_id=permission.id,
                    )
                )

            await session.commit()

            return tenant, invited_role

    finally:
        await engine.dispose()


async def create_existing_member(
    *,
    email: str,
    tenant_id: UUID,
    role_id: UUID,
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
            user = User(
                email=email,
                password_hash="unused-password-hash",
                first_name="Existing",
                last_name="Member",
                is_active=True,
            )

            session.add(user)
            await session.flush()

            session.add(
                Membership(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    role_id=role_id,
                    status=MembershipStatus.ACTIVE,
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
async def test_invite_member_endpoint_creates_invitation() -> None:
    unique = uuid4()

    inviter_email = f"inviter-{unique}@example.com"
    inviter_password = "very-secure-invitation-password"
    invited_email = f"invited-{unique}@example.com"

    tenant_slug = f"invitation-tenant-{unique}"
    inviter_role_name = f"inviter-role-{unique}"
    invited_role_name = f"invited-role-{unique}"

    tenant, invited_role = await create_invitation_context(
        inviter_email=inviter_email,
        inviter_password=inviter_password,
        tenant_slug=tenant_slug,
        inviter_role_name=inviter_role_name,
        invited_role_name=invited_role_name,
        grant_membership_manage=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=inviter_email,
            password=inviter_password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invitations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "email": invited_email,
                    "role_id": str(invited_role.id),
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["role_id"] == str(invited_role.id)
        assert body["email"] == invited_email
        assert body["status"] == "pending"
        assert body["expires_at"]
        assert body["accepted_at"] is None

    finally:
        await cleanup_test_data(
            emails=[
                inviter_email,
                invited_email,
            ],
            tenant_slug=tenant_slug,
            role_names=[
                inviter_role_name,
                invited_role_name,
            ],
        )


@pytest.mark.integration
async def test_invite_member_endpoint_requires_permission() -> None:
    unique = uuid4()

    inviter_email = f"no-permission-{unique}@example.com"
    inviter_password = "very-secure-invitation-password"

    tenant_slug = f"invitation-tenant-{unique}"
    inviter_role_name = f"no-permission-role-{unique}"
    invited_role_name = f"invited-role-{unique}"

    tenant, invited_role = await create_invitation_context(
        inviter_email=inviter_email,
        inviter_password=inviter_password,
        tenant_slug=tenant_slug,
        inviter_role_name=inviter_role_name,
        invited_role_name=invited_role_name,
        grant_membership_manage=False,
    )

    try:
        access_token = login_and_get_access_token(
            email=inviter_email,
            password=inviter_password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invitations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "email": f"target-{unique}@example.com",
                    "role_id": str(invited_role.id),
                },
            )

        assert response.status_code == 403
        assert response.json() == {"detail": "Permission denied"}

    finally:
        await cleanup_test_data(
            emails=[inviter_email],
            tenant_slug=tenant_slug,
            role_names=[
                inviter_role_name,
                invited_role_name,
            ],
        )


@pytest.mark.integration
async def test_invite_member_endpoint_rejects_duplicate_pending_invitation() -> None:
    unique = uuid4()

    inviter_email = f"duplicate-inviter-{unique}@example.com"
    inviter_password = "very-secure-invitation-password"
    invited_email = f"duplicate-target-{unique}@example.com"

    tenant_slug = f"invitation-tenant-{unique}"
    inviter_role_name = f"inviter-role-{unique}"
    invited_role_name = f"invited-role-{unique}"

    tenant, invited_role = await create_invitation_context(
        inviter_email=inviter_email,
        inviter_password=inviter_password,
        tenant_slug=tenant_slug,
        inviter_role_name=inviter_role_name,
        invited_role_name=invited_role_name,
        grant_membership_manage=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=inviter_email,
            password=inviter_password,
        )

        with TestClient(app) as client:
            first_response = client.post(
                f"/api/v1/tenants/{tenant.id}/invitations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "email": invited_email,
                    "role_id": str(invited_role.id),
                },
            )

            second_response = client.post(
                f"/api/v1/tenants/{tenant.id}/invitations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "email": invited_email,
                    "role_id": str(invited_role.id),
                },
            )

        assert first_response.status_code == 201
        assert second_response.status_code == 409

        assert second_response.json() == {"detail": "A pending invitation already exists"}

    finally:
        await cleanup_test_data(
            emails=[
                inviter_email,
                invited_email,
            ],
            tenant_slug=tenant_slug,
            role_names=[
                inviter_role_name,
                invited_role_name,
            ],
        )


@pytest.mark.integration
async def test_invite_member_endpoint_rejects_existing_member() -> None:
    unique = uuid4()

    inviter_email = f"existing-inviter-{unique}@example.com"
    inviter_password = "very-secure-invitation-password"
    existing_email = f"existing-member-{unique}@example.com"

    tenant_slug = f"invitation-tenant-{unique}"
    inviter_role_name = f"inviter-role-{unique}"
    invited_role_name = f"invited-role-{unique}"

    tenant, invited_role = await create_invitation_context(
        inviter_email=inviter_email,
        inviter_password=inviter_password,
        tenant_slug=tenant_slug,
        inviter_role_name=inviter_role_name,
        invited_role_name=invited_role_name,
        grant_membership_manage=True,
    )

    await create_existing_member(
        email=existing_email,
        tenant_id=tenant.id,
        role_id=invited_role.id,
    )

    try:
        access_token = login_and_get_access_token(
            email=inviter_email,
            password=inviter_password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invitations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "email": existing_email,
                    "role_id": str(invited_role.id),
                },
            )

        assert response.status_code == 409

        assert response.json() == {"detail": "User is already a member of this tenant"}

    finally:
        await cleanup_test_data(
            emails=[
                inviter_email,
                existing_email,
            ],
            tenant_slug=tenant_slug,
            role_names=[
                inviter_role_name,
                invited_role_name,
            ],
        )
