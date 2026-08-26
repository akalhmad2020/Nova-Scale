from datetime import UTC, datetime
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
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
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


async def create_read_context(
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
                last_name="Reader",
                is_active=True,
            )

            tenant = Tenant(
                name="Location Read Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Location read integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.LOCATION_READ)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.LOCATION_READ,
                    description="Read locations",
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


async def create_location(
    *,
    tenant_id: UUID,
    name: str,
    code: str,
    deleted: bool = False,
) -> Location:
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
            location = Location(
                tenant_id=tenant_id,
                name=name,
                code=code,
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Industrial Zone",
                status=LocationStatus.ACTIVE,
            )

            if deleted:
                location.deleted_at = datetime.now(UTC)

            session.add(location)
            await session.commit()

            return location

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
async def test_list_locations_endpoint_returns_tenant_locations() -> None:
    unique = uuid4()

    email = f"location-read-{unique}@example.com"
    password = "very-secure-location-password"
    tenant_slug = f"location-read-tenant-{unique}"
    role_name = f"location-read-role-{unique}"

    tenant = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        first = await create_location(
            tenant_id=tenant.id,
            name="First Warehouse",
            code="WH-001",
        )

        second = await create_location(
            tenant_id=tenant.id,
            name="Second Warehouse",
            code="WH-002",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/locations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 2

        returned_ids = {item["id"] for item in body}

        assert returned_ids == {
            str(first.id),
            str(second.id),
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_locations_endpoint_excludes_soft_deleted_locations() -> None:
    unique = uuid4()

    email = f"location-read-soft-{unique}@example.com"
    password = "very-secure-location-password"
    tenant_slug = f"location-read-soft-{unique}"
    role_name = f"location-read-soft-role-{unique}"

    tenant = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        active = await create_location(
            tenant_id=tenant.id,
            name="Active Warehouse",
            code="ACTIVE-001",
        )

        await create_location(
            tenant_id=tenant.id,
            name="Deleted Warehouse",
            code="DELETED-001",
            deleted=True,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/locations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1
        assert body[0]["id"] == str(active.id)

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_locations_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"location-read-denied-{unique}@example.com"
    password = "very-secure-location-password"
    tenant_slug = f"location-read-denied-{unique}"
    role_name = f"location-read-denied-role-{unique}"

    tenant = await create_read_context(
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
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/locations",
                headers={
                    "Authorization": f"Bearer {access_token}",
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
async def test_get_location_endpoint_returns_location() -> None:
    unique = uuid4()

    email = f"location-detail-{unique}@example.com"
    password = "very-secure-location-password"
    tenant_slug = f"location-detail-{unique}"
    role_name = f"location-detail-role-{unique}"

    tenant = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        location = await create_location(
            tenant_id=tenant.id,
            name="Main Warehouse",
            code="WH-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/locations/{location.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(location.id)
        assert body["tenant_id"] == str(tenant.id)
        assert body["name"] == "Main Warehouse"
        assert body["code"] == "WH-001"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_get_location_endpoint_rejects_unknown_location() -> None:
    unique = uuid4()

    email = f"location-missing-{unique}@example.com"
    password = "very-secure-location-password"
    tenant_slug = f"location-missing-{unique}"
    role_name = f"location-missing-role-{unique}"

    tenant = await create_read_context(
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
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/locations/{uuid4()}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Location not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )


@pytest.mark.integration
async def test_get_location_endpoint_rejects_location_from_other_tenant() -> None:
    unique = uuid4()

    first_email = f"location-first-{unique}@example.com"
    second_email = f"location-second-{unique}@example.com"

    password = "very-secure-location-password"

    first_slug = f"location-first-{unique}"
    second_slug = f"location-second-{unique}"

    first_role = f"location-first-role-{unique}"
    second_role = f"location-second-role-{unique}"

    first_tenant = await create_read_context(
        email=first_email,
        password=password,
        tenant_slug=first_slug,
        role_name=first_role,
        assign_permission=True,
    )

    second_tenant = await create_read_context(
        email=second_email,
        password=password,
        tenant_slug=second_slug,
        role_name=second_role,
        assign_permission=True,
    )

    try:
        foreign_location = await create_location(
            tenant_id=second_tenant.id,
            name="Foreign Warehouse",
            code="FOREIGN-001",
        )

        access_token = login_and_get_access_token(
            email=first_email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{first_tenant.id}/locations/{foreign_location.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Location not found"}

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


@pytest.mark.integration
async def test_get_location_endpoint_rejects_soft_deleted_location() -> None:
    unique = uuid4()

    email = f"location-deleted-{unique}@example.com"
    password = "very-secure-location-password"
    tenant_slug = f"location-deleted-{unique}"
    role_name = f"location-deleted-role-{unique}"

    tenant = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        location = await create_location(
            tenant_id=tenant.id,
            name="Deleted Warehouse",
            code="DELETED-001",
            deleted=True,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/locations/{location.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Location not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slug=tenant_slug,
            role_name=role_name,
        )
