from datetime import UTC, datetime, timedelta
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
    InvitationStatus,
    TenantStatus,
)
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.invitation import Invitation
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)


async def cleanup_test_data(
    *,
    emails: list[str],
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
            user_ids = list(
                (await session.execute(select(User.id).where(User.email.in_(emails)))).scalars()
            )

            tenant_id = await session.scalar(select(Tenant.id).where(Tenant.slug == tenant_slug))

            role_id = await session.scalar(select(Role.id).where(Role.name == role_name))

            if user_ids:
                await session.execute(delete(AuthSession).where(AuthSession.user_id.in_(user_ids)))

                await session.execute(delete(Membership).where(Membership.user_id.in_(user_ids)))

            if tenant_id is not None:
                await session.execute(delete(Invitation).where(Invitation.tenant_id == tenant_id))

                await session.execute(delete(Membership).where(Membership.tenant_id == tenant_id))

            if user_ids:
                await session.execute(delete(User).where(User.id.in_(user_ids)))

            if tenant_id is not None:
                await session.execute(delete(Tenant).where(Tenant.id == tenant_id))

            if role_id is not None:
                await session.execute(delete(Role).where(Role.id == role_id))

            await session.commit()

    finally:
        await engine.dispose()


async def create_accept_context(
    *,
    invited_email: str,
    invited_password: str,
    tenant_slug: str,
    role_name: str,
    invitation_status: InvitationStatus = InvitationStatus.PENDING,
    expires_at: datetime | None = None,
) -> tuple[User, Tenant, Role, Invitation]:
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
                email=invited_email,
                password_hash=password_hasher.hash(invited_password),
                first_name="Invited",
                last_name="User",
                is_active=True,
            )

            tenant = Tenant(
                name="Invitation Accept Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Invitation accept test role",
            )

            session.add_all(
                [
                    user,
                    tenant,
                    role,
                ]
            )

            await session.flush()

            invitation = Invitation(
                tenant_id=tenant.id,
                role_id=role.id,
                email=invited_email,
                status=invitation_status,
                expires_at=expires_at or datetime.now(UTC) + timedelta(days=7),
            )

            session.add(invitation)

            await session.commit()

            return user, tenant, role, invitation

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


async def get_membership(
    *,
    user_id: UUID,
    tenant_id: UUID,
) -> Membership | None:
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
            membership = await session.scalar(
                select(Membership).where(
                    Membership.user_id == user_id,
                    Membership.tenant_id == tenant_id,
                )
            )

            return membership

    finally:
        await engine.dispose()


@pytest.mark.integration
async def test_accept_invitation_endpoint_creates_membership() -> None:
    unique = uuid4()

    email = f"accept-{unique}@example.com"
    password = "very-secure-invitation-password"
    tenant_slug = f"accept-tenant-{unique}"
    role_name = f"accept-role-{unique}"

    user, tenant, role, invitation = await create_accept_context(
        invited_email=email,
        invited_password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/invitations/{invitation.id}/accept",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["user_id"] == str(user.id)
        assert body["tenant_id"] == str(tenant.id)
        assert body["role_id"] == str(role.id)

        membership = await get_membership(
            user_id=user.id,
            tenant_id=tenant.id,
        )

        assert membership is not None
        assert membership.role_id == role.id

    finally:
        await cleanup_test_data(
            emails=[email],
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_accept_invitation_endpoint_marks_invitation_accepted() -> None:
    unique = uuid4()

    email = f"accepted-{unique}@example.com"
    password = "very-secure-invitation-password"
    tenant_slug = f"accepted-tenant-{unique}"
    role_name = f"accepted-role-{unique}"

    _, _, _, invitation = await create_accept_context(
        invited_email=email,
        invited_password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/invitations/{invitation.id}/accept",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

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
                stored = await session.get(
                    Invitation,
                    invitation.id,
                )

                assert stored is not None
                assert stored.status is InvitationStatus.ACCEPTED
                assert stored.accepted_at is not None

        finally:
            await engine.dispose()

    finally:
        await cleanup_test_data(
            emails=[email],
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_accept_invitation_endpoint_rejects_second_accept() -> None:
    unique = uuid4()

    email = f"double-{unique}@example.com"
    password = "very-secure-invitation-password"
    tenant_slug = f"double-tenant-{unique}"
    role_name = f"double-role-{unique}"

    _, _, _, invitation = await create_accept_context(
        invited_email=email,
        invited_password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            first_response = client.post(
                f"/api/v1/invitations/{invitation.id}/accept",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

            second_response = client.post(
                f"/api/v1/invitations/{invitation.id}/accept",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert first_response.status_code == 200
        assert second_response.status_code == 409

        assert second_response.json() == {"detail": "Invitation is no longer pending"}

    finally:
        await cleanup_test_data(
            emails=[email],
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_accept_invitation_endpoint_rejects_wrong_user() -> None:
    unique = uuid4()

    invited_email = f"invited-{unique}@example.com"
    wrong_email = f"wrong-{unique}@example.com"

    password = "very-secure-invitation-password"
    tenant_slug = f"wrong-user-tenant-{unique}"
    role_name = f"wrong-user-role-{unique}"

    _, _, _, invitation = await create_accept_context(
        invited_email=invited_email,
        invited_password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
    )

    await create_accept_context(
        invited_email=wrong_email,
        invited_password=password,
        tenant_slug=f"temporary-{unique}",
        role_name=f"temporary-role-{unique}",
    )

    try:
        access_token = login_and_get_access_token(
            email=wrong_email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/invitations/{invitation.id}/accept",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 403

        assert response.json() == {"detail": "Invitation does not belong to the current user"}

    finally:
        await cleanup_test_data(
            emails=[
                invited_email,
                wrong_email,
            ],
            tenant_slug=tenant_slug,
            role_name=role_name,
        )

        await cleanup_test_data(
            emails=[wrong_email],
            tenant_slug=f"temporary-{unique}",
            role_name=f"temporary-role-{unique}",
        )


@pytest.mark.integration
async def test_accept_invitation_endpoint_rejects_expired_invitation() -> None:
    unique = uuid4()

    email = f"expired-{unique}@example.com"
    password = "very-secure-invitation-password"
    tenant_slug = f"expired-tenant-{unique}"
    role_name = f"expired-role-{unique}"

    _, _, _, invitation = await create_accept_context(
        invited_email=email,
        invited_password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/invitations/{invitation.id}/accept",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 410
        assert response.json() == {"detail": "Invitation has expired"}

    finally:
        await cleanup_test_data(
            emails=[email],
            tenant_slug=tenant_slug,
            role_name=role_name,
        )
