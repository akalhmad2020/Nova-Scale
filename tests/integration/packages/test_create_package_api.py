from decimal import Decimal
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
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location
from app.modules.packages.infrastructure.models.package import Package
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment


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
                await session.execute(delete(Package).where(Package.tenant_id.in_(tenant_ids)))

                await session.execute(delete(Shipment).where(Shipment.tenant_id.in_(tenant_ids)))

                await session.execute(delete(Customer).where(Customer.tenant_id.in_(tenant_ids)))

                await session.execute(delete(Location).where(Location.tenant_id.in_(tenant_ids)))

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


async def create_package_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
    assign_permission: bool,
) -> tuple[Tenant, Shipment]:
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
                first_name="Package",
                last_name="Manager",
                is_active=True,
            )

            tenant = Tenant(
                name="Packages Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Packages integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.PACKAGE_CREATE)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.PACKAGE_CREATE,
                    description="Create packages",
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

            customer = Customer(
                tenant_id=tenant.id,
                name="Package Customer",
                code="PKG-CUST-001",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Package Origin",
                code="PKG-ORIGIN",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Package Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Package Destination",
                code="PKG-DEST",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Nablus",
                address_line1="Package Destination Address",
                status=LocationStatus.ACTIVE,
            )

            session.add_all(
                [
                    customer,
                    origin,
                    destination,
                ]
            )

            await session.flush()

            shipment = Shipment(
                tenant_id=tenant.id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
                tracking_number=f"PKG-SHIP-{uuid4()}",
                status=ShipmentStatus.DRAFT,
                service_type=ServiceType.STANDARD,
                weight=Decimal("20.000"),
                weight_unit=WeightUnit.KG,
            )

            session.add(shipment)

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

            return (
                tenant,
                shipment,
            )

    finally:
        await engine.dispose()


async def create_foreign_shipment(
    *,
    tenant_slug: str,
) -> tuple[Tenant, Shipment]:
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
                name="Foreign Package Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Package Customer",
                code="FOREIGN-PKG-CUST",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Foreign Package Origin",
                code="FOREIGN-PKG-ORIGIN",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Hebron",
                address_line1="Foreign Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Foreign Package Destination",
                code="FOREIGN-PKG-DEST",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Jenin",
                address_line1="Foreign Destination Address",
                status=LocationStatus.ACTIVE,
            )

            session.add_all(
                [
                    customer,
                    origin,
                    destination,
                ]
            )

            await session.flush()

            shipment = Shipment(
                tenant_id=tenant.id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
                tracking_number=f"FOREIGN-PKG-SHIP-{uuid4()}",
                status=ShipmentStatus.DRAFT,
                service_type=ServiceType.STANDARD,
                weight=Decimal("10.000"),
                weight_unit=WeightUnit.KG,
            )

            session.add(shipment)

            await session.commit()

            return (
                tenant,
                shipment,
            )

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


def package_payload(
    *,
    package_number: str,
) -> dict[str, object]:
    return {
        "package_number": package_number,
        "description": "  Electronics package  ",
        "weight": "4.500",
        "weight_unit": "kg",
        "length": "40.00",
        "width": "30.00",
        "height": "20.00",
        "dimension_unit": "cm",
        "notes": "  Fragile package  ",
    }


@pytest.mark.integration
async def test_create_package_endpoint_creates_package() -> None:
    unique = uuid4()

    email = f"package-create-{unique}@example.com"
    password = "very-secure-package-password"
    tenant_slug = f"package-tenant-{unique}"
    role_name = f"package-role-{unique}"

    tenant, shipment = await create_package_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/packages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=package_payload(
                    package_number="  pkg-001  ",
                ),
            )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["shipment_id"] == str(shipment.id)

        assert body["package_number"] == "PKG-001"
        assert body["description"] == "Electronics package"

        assert body["weight"] == "4.500"
        assert body["weight_unit"] == "kg"

        assert body["length"] == "40.00"
        assert body["width"] == "30.00"
        assert body["height"] == "20.00"
        assert body["dimension_unit"] == "cm"

        assert body["notes"] == "Fragile package"
        assert body["id"]

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_package_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"package-denied-{unique}@example.com"
    password = "very-secure-package-password"
    tenant_slug = f"package-denied-tenant-{unique}"
    role_name = f"package-denied-role-{unique}"

    tenant, shipment = await create_package_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/packages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=package_payload(
                    package_number="DENIED-001",
                ),
            )

        assert response.status_code == 403
        assert response.json() == {"detail": "Permission denied"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_package_endpoint_rejects_duplicate_number() -> None:
    unique = uuid4()

    email = f"package-duplicate-{unique}@example.com"
    password = "very-secure-package-password"
    tenant_slug = f"package-duplicate-tenant-{unique}"
    role_name = f"package-duplicate-role-{unique}"

    tenant, shipment = await create_package_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/packages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=package_payload(
                    package_number="PKG-DUP-001",
                ),
            )

            second_response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/packages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=package_payload(
                    package_number=" pkg-dup-001 ",
                ),
            )

        assert first_response.status_code == 201

        assert second_response.status_code == 409
        assert second_response.json() == {"detail": "Package number already exists in shipment"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_package_endpoint_rejects_foreign_shipment() -> None:
    unique = uuid4()

    email = f"package-isolation-{unique}@example.com"
    password = "very-secure-package-password"

    tenant_slug = f"package-isolation-tenant-{unique}"
    foreign_slug = f"package-foreign-tenant-{unique}"
    role_name = f"package-isolation-role-{unique}"

    tenant, _ = await create_package_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    _, foreign_shipment = await create_foreign_shipment(
        tenant_slug=foreign_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{foreign_shipment.id}/packages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=package_payload(
                    package_number="FOREIGN-001",
                ),
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Shipment not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(
                tenant_slug,
                foreign_slug,
            ),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_package_endpoint_rejects_invalid_weight() -> None:
    unique = uuid4()

    email = f"package-weight-{unique}@example.com"
    password = "very-secure-package-password"
    tenant_slug = f"package-weight-tenant-{unique}"
    role_name = f"package-weight-role-{unique}"

    tenant, shipment = await create_package_context(
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

        payload = package_payload(
            package_number="INVALID-WEIGHT-001",
        )
        payload["weight"] = "0"

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/packages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=payload,
            )

        assert response.status_code == 422

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_package_endpoint_rejects_partial_dimensions() -> None:
    unique = uuid4()

    email = f"package-dimensions-{unique}@example.com"
    password = "very-secure-package-password"
    tenant_slug = f"package-dimensions-tenant-{unique}"
    role_name = f"package-dimensions-role-{unique}"

    tenant, shipment = await create_package_context(
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

        payload = package_payload(
            package_number="PARTIAL-DIM-001",
        )

        payload["width"] = None
        payload["height"] = None

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/packages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=payload,
            )

        assert response.status_code == 422

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_package_endpoint_rejects_dimension_unit_without_dimensions() -> None:
    unique = uuid4()

    email = f"package-unit-{unique}@example.com"
    password = "very-secure-package-password"
    tenant_slug = f"package-unit-tenant-{unique}"
    role_name = f"package-unit-role-{unique}"

    tenant, shipment = await create_package_context(
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

        payload = package_payload(
            package_number="UNIT-WITHOUT-DIMS-001",
        )

        payload["length"] = None
        payload["width"] = None
        payload["height"] = None
        payload["dimension_unit"] = "cm"

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/packages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=payload,
            )

        assert response.status_code == 422

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )
