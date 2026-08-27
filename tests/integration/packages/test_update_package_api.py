from decimal import Decimal
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
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location
from app.modules.packages.domain.enums import DimensionUnit
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


async def create_update_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
    assign_permission: bool,
) -> tuple[Tenant, Shipment, Shipment]:
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
                last_name="Updater",
                is_active=True,
            )

            tenant = Tenant(
                name="Package Update Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Package update integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.PACKAGE_UPDATE)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.PACKAGE_UPDATE,
                    description="Update packages",
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
                name="Package Update Customer",
                code=f"PKG-UPD-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Package Update Origin",
                code=f"PKG-UPD-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Package Update Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Package Update Destination",
                code=f"PKG-UPD-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Nablus",
                address_line1="Package Update Destination Address",
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

            first_shipment = Shipment(
                tenant_id=tenant.id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
                tracking_number=f"PKG-UPD-SHIP-1-{uuid4()}",
                status=ShipmentStatus.DRAFT,
                service_type=ServiceType.STANDARD,
                weight=Decimal("20.000"),
                weight_unit=WeightUnit.KG,
            )

            second_shipment = Shipment(
                tenant_id=tenant.id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
                tracking_number=f"PKG-UPD-SHIP-2-{uuid4()}",
                status=ShipmentStatus.DRAFT,
                service_type=ServiceType.STANDARD,
                weight=Decimal("30.000"),
                weight_unit=WeightUnit.KG,
            )

            session.add_all(
                [
                    first_shipment,
                    second_shipment,
                ]
            )

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
                first_shipment,
                second_shipment,
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
                name="Foreign Package Update Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Update Customer",
                code=f"FOREIGN-UPD-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Foreign Update Origin",
                code=f"FOREIGN-UPD-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Hebron",
                address_line1="Foreign Update Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Foreign Update Destination",
                code=f"FOREIGN-UPD-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Jenin",
                address_line1="Foreign Update Destination Address",
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
                tracking_number=f"FOREIGN-PKG-UPD-SHIP-{uuid4()}",
                status=ShipmentStatus.DRAFT,
                service_type=ServiceType.STANDARD,
                weight=Decimal("10.000"),
                weight_unit=WeightUnit.KG,
            )

            session.add(shipment)
            await session.commit()

            return tenant, shipment

    finally:
        await engine.dispose()


async def create_package(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
    package_number: str,
) -> Package:
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
            package = Package(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
                package_number=package_number,
                description="Old package description",
                weight=Decimal("1.000"),
                weight_unit=WeightUnit.KG,
                length=Decimal("10.00"),
                width=Decimal("20.00"),
                height=Decimal("30.00"),
                dimension_unit=DimensionUnit.CM,
                notes="Old package notes",
            )

            session.add(package)
            await session.commit()

            return package

    finally:
        await engine.dispose()


async def get_package_raw(
    package_id: UUID,
) -> Package | None:
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
            return await session.get(
                Package,
                package_id,
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


def update_payload(
    *,
    shipment_id: UUID,
    package_number: str,
) -> dict[str, object]:
    return {
        "shipment_id": str(shipment_id),
        "package_number": package_number,
        "description": "  Updated package description  ",
        "weight": "7.500",
        "weight_unit": "lb",
        "length": "50.00",
        "width": "40.00",
        "height": "30.00",
        "dimension_unit": "in",
        "notes": "  Updated package notes  ",
    }


@pytest.mark.integration
async def test_update_package_endpoint_updates_package() -> None:
    unique = uuid4()

    email = f"package-update-{unique}@example.com"
    password = "very-secure-package-password"
    tenant_slug = f"package-update-tenant-{unique}"
    role_name = f"package-update-role-{unique}"

    tenant, shipment, _ = await create_update_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        package = await create_package(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            package_number="OLD-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/tenants/{tenant.id}/packages/{package.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=update_payload(
                    shipment_id=shipment.id,
                    package_number="  new-001  ",
                ),
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(package.id)
        assert body["tenant_id"] == str(tenant.id)
        assert body["shipment_id"] == str(shipment.id)

        assert body["package_number"] == "NEW-001"
        assert body["description"] == "Updated package description"

        assert body["weight"] == "7.500"
        assert body["weight_unit"] == "lb"

        assert body["length"] == "50.00"
        assert body["width"] == "40.00"
        assert body["height"] == "30.00"
        assert body["dimension_unit"] == "in"

        assert body["notes"] == "Updated package notes"

        stored = await get_package_raw(package.id)

        assert stored is not None
        assert stored.package_number == "NEW-001"
        assert stored.weight == Decimal("7.500")

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_update_package_endpoint_can_move_package_to_another_shipment() -> None:
    unique = uuid4()

    email = f"package-move-{unique}@example.com"
    password = "very-secure-package-password"
    tenant_slug = f"package-move-tenant-{unique}"
    role_name = f"package-move-role-{unique}"

    tenant, first_shipment, second_shipment = await create_update_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        package = await create_package(
            tenant_id=tenant.id,
            shipment_id=first_shipment.id,
            package_number="MOVE-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/tenants/{tenant.id}/packages/{package.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=update_payload(
                    shipment_id=second_shipment.id,
                    package_number="MOVE-001",
                ),
            )

        assert response.status_code == 200
        assert response.json()["shipment_id"] == str(second_shipment.id)

        stored = await get_package_raw(package.id)

        assert stored is not None
        assert stored.shipment_id == second_shipment.id

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_update_package_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"package-update-denied-{unique}@example.com"
    password = "very-secure-package-password"
    tenant_slug = f"package-update-denied-tenant-{unique}"
    role_name = f"package-update-denied-role-{unique}"

    tenant, shipment, _ = await create_update_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=False,
    )

    try:
        package = await create_package(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            package_number="DENIED-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/tenants/{tenant.id}/packages/{package.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=update_payload(
                    shipment_id=shipment.id,
                    package_number="DENIED-UPDATED",
                ),
            )

        assert response.status_code == 403
        assert response.json() == {"detail": "Permission denied"}

        stored = await get_package_raw(package.id)

        assert stored is not None
        assert stored.package_number == "DENIED-001"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_update_package_endpoint_rejects_unknown_package() -> None:
    unique = uuid4()

    email = f"package-update-missing-{unique}@example.com"
    password = "very-secure-package-password"
    tenant_slug = f"package-update-missing-tenant-{unique}"
    role_name = f"package-update-missing-role-{unique}"

    tenant, shipment, _ = await create_update_context(
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
            response = client.patch(
                f"/api/v1/tenants/{tenant.id}/packages/{uuid4()}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=update_payload(
                    shipment_id=shipment.id,
                    package_number="MISSING-001",
                ),
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Package not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_update_package_endpoint_rejects_duplicate_number_in_target_shipment() -> None:
    unique = uuid4()

    email = f"package-update-duplicate-{unique}@example.com"
    password = "very-secure-package-password"
    tenant_slug = f"package-update-duplicate-tenant-{unique}"
    role_name = f"package-update-duplicate-role-{unique}"

    tenant, first_shipment, second_shipment = await create_update_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        package = await create_package(
            tenant_id=tenant.id,
            shipment_id=first_shipment.id,
            package_number="SOURCE-001",
        )

        await create_package(
            tenant_id=tenant.id,
            shipment_id=second_shipment.id,
            package_number="DUP-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/tenants/{tenant.id}/packages/{package.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=update_payload(
                    shipment_id=second_shipment.id,
                    package_number=" dup-001 ",
                ),
            )

        assert response.status_code == 409
        assert response.json() == {"detail": "Package number already exists in shipment"}

        stored = await get_package_raw(package.id)

        assert stored is not None
        assert stored.shipment_id == first_shipment.id
        assert stored.package_number == "SOURCE-001"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_update_package_endpoint_rejects_foreign_shipment() -> None:
    unique = uuid4()

    email = f"package-update-foreign-{unique}@example.com"
    password = "very-secure-package-password"

    tenant_slug = f"package-update-tenant-{unique}"
    foreign_slug = f"package-update-foreign-tenant-{unique}"
    role_name = f"package-update-foreign-role-{unique}"

    tenant, shipment, _ = await create_update_context(
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
        package = await create_package(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            package_number="FOREIGN-SHIP-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/tenants/{tenant.id}/packages/{package.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=update_payload(
                    shipment_id=foreign_shipment.id,
                    package_number="FOREIGN-SHIP-UPDATED",
                ),
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Shipment not found"}

        stored = await get_package_raw(package.id)

        assert stored is not None
        assert stored.shipment_id == shipment.id

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
async def test_update_package_endpoint_rejects_invalid_dimensions() -> None:
    unique = uuid4()

    email = f"package-update-dims-{unique}@example.com"
    password = "very-secure-package-password"
    tenant_slug = f"package-update-dims-tenant-{unique}"
    role_name = f"package-update-dims-role-{unique}"

    tenant, shipment, _ = await create_update_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        package = await create_package(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            package_number="DIMS-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        payload = update_payload(
            shipment_id=shipment.id,
            package_number="DIMS-UPDATED",
        )
        payload["width"] = None

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/tenants/{tenant.id}/packages/{package.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=payload,
            )

        assert response.status_code == 422

        stored = await get_package_raw(package.id)

        assert stored is not None
        assert stored.package_number == "DIMS-001"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )
