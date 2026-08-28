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
from app.modules.carriers.domain.enums import (
    CarrierServiceStatus,
    CarrierStatus,
)
from app.modules.carriers.infrastructure.models.carrier import Carrier
from app.modules.carriers.infrastructure.models.carrier_service import (
    CarrierService,
)
from app.modules.identity.domain.enums import MembershipStatus, TenantStatus
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
from app.modules.shipments.domain.enums import ServiceType


async def cleanup_test_data(
    *,
    email: str,
    tenant_slugs: tuple[str, ...],
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

            tenant_ids = list(
                (
                    await session.scalars(select(Tenant.id).where(Tenant.slug.in_(tenant_slugs)))
                ).all()
            )

            role_id = await session.scalar(select(Role.id).where(Role.name == role_name))

            if tenant_ids:
                await session.execute(
                    delete(CarrierService).where(CarrierService.tenant_id.in_(tenant_ids))
                )

                await session.execute(delete(Carrier).where(Carrier.tenant_id.in_(tenant_ids)))

            if user_id is not None:
                await session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))

                await session.execute(delete(Membership).where(Membership.user_id == user_id))

            if tenant_ids:
                await session.execute(
                    delete(Membership).where(Membership.tenant_id.in_(tenant_ids))
                )

            if role_id is not None:
                await session.execute(
                    delete(RolePermission).where(RolePermission.role_id == role_id)
                )

            if user_id is not None:
                await session.execute(delete(User).where(User.id == user_id))

            if tenant_ids:
                await session.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))

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
                first_name="CarrierService",
                last_name="Reader",
                is_active=True,
            )

            tenant = Tenant(
                name="Carrier Service Read Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Carrier service read integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.CARRIER_SERVICE_READ)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.CARRIER_SERVICE_READ,
                    description="Read carrier services",
                )
                session.add(permission)

            session.add_all([user, tenant, role])
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


async def create_tenant(
    *,
    tenant_slug: str,
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

    try:
        async with session_factory() as session:
            tenant = Tenant(
                name="Foreign Carrier Service Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.commit()

            return tenant

    finally:
        await engine.dispose()


async def create_carrier(
    *,
    tenant_id: UUID,
    code: str,
) -> Carrier:
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
            carrier = Carrier(
                tenant_id=tenant_id,
                code=code,
                name=f"{code} Carrier",
                status=CarrierStatus.ACTIVE,
            )

            session.add(carrier)
            await session.commit()

            return carrier

    finally:
        await engine.dispose()


async def create_carrier_service(
    *,
    tenant_id: UUID,
    carrier_id: UUID,
    code: str,
    name: str,
    service_type: ServiceType = ServiceType.STANDARD,
) -> CarrierService:
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
            service = CarrierService(
                tenant_id=tenant_id,
                carrier_id=carrier_id,
                code=code,
                name=name,
                service_type=service_type,
                status=CarrierServiceStatus.ACTIVE,
            )

            session.add(service)
            await session.commit()

            return service

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
async def test_list_carrier_services_endpoint_returns_services() -> None:
    unique = uuid4()

    email = f"carrier-service-read-list-{unique}@example.com"
    password = "very-secure-carrier-password"
    tenant_slug = f"carrier-service-read-list-tenant-{unique}"
    role_name = f"carrier-service-read-list-role-{unique}"

    tenant = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        carrier = await create_carrier(
            tenant_id=tenant.id,
            code="DHL",
        )

        first = await create_carrier_service(
            tenant_id=tenant.id,
            carrier_id=carrier.id,
            code="STANDARD",
            name="Standard Service",
        )

        second = await create_carrier_service(
            tenant_id=tenant.id,
            carrier_id=carrier.id,
            code="EXPRESS",
            name="Express Service",
            service_type=ServiceType.EXPRESS,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                (f"/api/v1/tenants/{tenant.id}/carriers/{carrier.id}/services"),
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
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_carrier_services_endpoint_returns_empty_list() -> None:
    unique = uuid4()

    email = f"carrier-service-read-empty-{unique}@example.com"
    password = "very-secure-carrier-password"
    tenant_slug = f"carrier-service-read-empty-tenant-{unique}"
    role_name = f"carrier-service-read-empty-role-{unique}"

    tenant = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        carrier = await create_carrier(
            tenant_id=tenant.id,
            code="DHL",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                (f"/api/v1/tenants/{tenant.id}/carriers/{carrier.id}/services"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200
        assert response.json() == []

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_carrier_services_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"carrier-service-read-denied-{unique}@example.com"
    password = "very-secure-carrier-password"
    tenant_slug = f"carrier-service-read-denied-tenant-{unique}"
    role_name = f"carrier-service-read-denied-role-{unique}"

    tenant = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=False,
    )

    try:
        carrier = await create_carrier(
            tenant_id=tenant.id,
            code="DHL",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                (f"/api/v1/tenants/{tenant.id}/carriers/{carrier.id}/services"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 403
        assert response.json() == {
            "detail": "Permission denied",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_carrier_services_endpoint_hides_foreign_carrier() -> None:
    unique = uuid4()

    email = f"carrier-service-read-foreign-carrier-{unique}@example.com"
    password = "very-secure-carrier-password"
    tenant_slug = f"carrier-service-read-own-tenant-{unique}"
    foreign_tenant_slug = f"carrier-service-read-foreign-tenant-{unique}"
    role_name = f"carrier-service-read-foreign-role-{unique}"

    tenant = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    foreign_tenant = await create_tenant(
        tenant_slug=foreign_tenant_slug,
    )

    try:
        foreign_carrier = await create_carrier(
            tenant_id=foreign_tenant.id,
            code="FOREIGN",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                (f"/api/v1/tenants/{tenant.id}/carriers/{foreign_carrier.id}/services"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(
                tenant_slug,
                foreign_tenant_slug,
            ),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_get_carrier_service_endpoint_returns_service() -> None:
    unique = uuid4()

    email = f"carrier-service-read-get-{unique}@example.com"
    password = "very-secure-carrier-password"
    tenant_slug = f"carrier-service-read-get-tenant-{unique}"
    role_name = f"carrier-service-read-get-role-{unique}"

    tenant = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        carrier = await create_carrier(
            tenant_id=tenant.id,
            code="DHL",
        )

        service = await create_carrier_service(
            tenant_id=tenant.id,
            carrier_id=carrier.id,
            code="EXPRESS",
            name="Express Delivery",
            service_type=ServiceType.EXPRESS,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                (f"/api/v1/tenants/{tenant.id}/carrier-services/{service.id}"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(service.id)
        assert body["tenant_id"] == str(tenant.id)
        assert body["carrier_id"] == str(carrier.id)
        assert body["code"] == "EXPRESS"
        assert body["name"] == "Express Delivery"
        assert body["service_type"] == "express"
        assert body["status"] == "active"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_get_carrier_service_endpoint_hides_foreign_service() -> None:
    unique = uuid4()

    email = f"carrier-service-read-foreign-{unique}@example.com"
    password = "very-secure-carrier-password"
    tenant_slug = f"carrier-service-read-own-service-tenant-{unique}"
    foreign_tenant_slug = f"carrier-service-read-foreign-service-tenant-{unique}"
    role_name = f"carrier-service-read-foreign-service-role-{unique}"

    tenant = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    foreign_tenant = await create_tenant(
        tenant_slug=foreign_tenant_slug,
    )

    try:
        foreign_carrier = await create_carrier(
            tenant_id=foreign_tenant.id,
            code="FOREIGN",
        )

        foreign_service = await create_carrier_service(
            tenant_id=foreign_tenant.id,
            carrier_id=foreign_carrier.id,
            code="EXPRESS",
            name="Foreign Express",
            service_type=ServiceType.EXPRESS,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                (f"/api/v1/tenants/{tenant.id}/carrier-services/{foreign_service.id}"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(
                tenant_slug,
                foreign_tenant_slug,
            ),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_get_carrier_service_endpoint_returns_not_found_for_unknown_service() -> None:
    unique = uuid4()

    email = f"carrier-service-read-missing-{unique}@example.com"
    password = "very-secure-carrier-password"
    tenant_slug = f"carrier-service-read-missing-tenant-{unique}"
    role_name = f"carrier-service-read-missing-role-{unique}"

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

        missing_service_id = uuid4()

        with TestClient(app) as client:
            response = client.get(
                (f"/api/v1/tenants/{tenant.id}/carrier-services/{missing_service_id}"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )
