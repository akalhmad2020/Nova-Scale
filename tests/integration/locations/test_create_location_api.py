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
from app.modules.locations.infrastructure.models.location import Location


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
                await session.execute(delete(Location).where(Location.tenant_id == tenant_id))

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


async def create_location_context(
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
                first_name="Location",
                last_name="Manager",
                is_active=True,
            )

            tenant = Tenant(
                name="Locations Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Locations integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.LOCATION_CREATE)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.LOCATION_CREATE,
                    description="Create locations",
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
async def test_create_location_endpoint_creates_location() -> None:
    unique = uuid4()

    email = f"location-create-{unique}@example.com"
    password = "very-secure-location-password"
    tenant_slug = f"location-tenant-{unique}"
    role_name = f"location-role-{unique}"

    tenant = await create_location_context(
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
                f"/api/v1/tenants/{tenant.id}/locations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "  Main Warehouse  ",
                    "code": "  wh-001  ",
                    "type": "warehouse",
                    "country_code": "ps",
                    "state": "  Ramallah and Al-Bireh  ",
                    "city": "  Ramallah  ",
                    "postal_code": "  P600  ",
                    "address_line1": "  Industrial Zone  ",
                    "address_line2": "  Building 10  ",
                    "contact_name": "  Warehouse Manager  ",
                    "email": "WAREHOUSE@EXAMPLE.COM",
                    "phone": "  +970599000000  ",
                    "latitude": "31.903800",
                    "longitude": "35.203400",
                    "notes": "  Main distribution warehouse  ",
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["name"] == "Main Warehouse"
        assert body["code"] == "WH-001"
        assert body["type"] == "warehouse"

        assert body["country_code"] == "PS"
        assert body["state"] == "Ramallah and Al-Bireh"
        assert body["city"] == "Ramallah"
        assert body["postal_code"] == "P600"
        assert body["address_line1"] == "Industrial Zone"
        assert body["address_line2"] == "Building 10"

        assert body["contact_name"] == "Warehouse Manager"
        assert body["email"] == "warehouse@example.com"
        assert body["phone"] == "+970599000000"

        assert body["latitude"] == "31.903800"
        assert body["longitude"] == "35.203400"

        assert body["notes"] == "Main distribution warehouse"
        assert body["status"] == "active"
        assert body["id"]

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_location_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"location-denied-{unique}@example.com"
    password = "very-secure-location-password"
    tenant_slug = f"location-denied-tenant-{unique}"
    role_name = f"location-denied-role-{unique}"

    tenant = await create_location_context(
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
                f"/api/v1/tenants/{tenant.id}/locations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "Denied Warehouse",
                    "code": "DENIED-001",
                    "type": "warehouse",
                    "country_code": "PS",
                    "city": "Ramallah",
                    "address_line1": "Industrial Zone",
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
async def test_create_location_endpoint_rejects_duplicate_code() -> None:
    unique = uuid4()

    email = f"location-duplicate-{unique}@example.com"
    password = "very-secure-location-password"
    tenant_slug = f"location-duplicate-tenant-{unique}"
    role_name = f"location-duplicate-role-{unique}"

    tenant = await create_location_context(
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
                f"/api/v1/tenants/{tenant.id}/locations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "First Warehouse",
                    "code": "WH-001",
                    "type": "warehouse",
                    "country_code": "PS",
                    "city": "Ramallah",
                    "address_line1": "Industrial Zone",
                },
            )

            second_response = client.post(
                f"/api/v1/tenants/{tenant.id}/locations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "Second Warehouse",
                    "code": " wh-001 ",
                    "type": "warehouse",
                    "country_code": "PS",
                    "city": "Nablus",
                    "address_line1": "Industrial Area",
                },
            )

        assert first_response.status_code == 201
        assert second_response.status_code == 409
        assert second_response.json() == {"detail": "Location code already exists"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )
