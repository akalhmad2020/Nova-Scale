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


async def create_shipment_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
    assign_permission: bool,
) -> tuple[Tenant, Customer, Location, Location]:
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
                first_name="Shipment",
                last_name="Manager",
                is_active=True,
            )

            tenant = Tenant(
                name="Shipments Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Shipments integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.SHIPMENT_CREATE)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.SHIPMENT_CREATE,
                    description="Create shipments",
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
                name="Acme Trading",
                code="ACME-001",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Origin Warehouse",
                code="ORIGIN-001",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Origin Industrial Zone",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Destination Warehouse",
                code="DEST-001",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Nablus",
                address_line1="Destination Industrial Zone",
                status=LocationStatus.ACTIVE,
            )

            session.add_all(
                [
                    customer,
                    origin,
                    destination,
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
                customer,
                origin,
                destination,
            )

    finally:
        await engine.dispose()


async def create_foreign_resources(
    *,
    tenant_slug: str,
) -> tuple[Tenant, Customer, Location, Location]:
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
                name="Foreign Shipments Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Customer",
                code="FOREIGN-001",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Foreign Origin",
                code="FOREIGN-ORIGIN",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Hebron",
                address_line1="Foreign Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Foreign Destination",
                code="FOREIGN-DEST",
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

            await session.commit()

            return (
                tenant,
                customer,
                origin,
                destination,
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


def shipment_payload(
    *,
    customer_id: str,
    origin_location_id: str,
    destination_location_id: str,
    tracking_number: str,
) -> dict[str, object]:
    return {
        "customer_id": customer_id,
        "origin_location_id": origin_location_id,
        "destination_location_id": destination_location_id,
        "tracking_number": tracking_number,
        "reference": "  REF-001  ",
        "service_type": "express",
        "description": "  Integration shipment  ",
        "weight": "12.500",
        "weight_unit": "kg",
        "notes": "  Handle carefully  ",
    }


@pytest.mark.integration
async def test_create_shipment_endpoint_creates_shipment() -> None:
    unique = uuid4()

    email = f"shipment-create-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-tenant-{unique}"
    role_name = f"shipment-role-{unique}"

    tenant, customer, origin, destination = await create_shipment_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=shipment_payload(
                    customer_id=str(customer.id),
                    origin_location_id=str(origin.id),
                    destination_location_id=str(destination.id),
                    tracking_number="  ship-001  ",
                ),
            )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["customer_id"] == str(customer.id)
        assert body["origin_location_id"] == str(origin.id)
        assert body["destination_location_id"] == str(destination.id)

        assert body["tracking_number"] == "SHIP-001"
        assert body["reference"] == "REF-001"
        assert body["status"] == "draft"
        assert body["service_type"] == "express"
        assert body["description"] == "Integration shipment"
        assert body["weight"] == "12.500"
        assert body["weight_unit"] == "kg"
        assert body["notes"] == "Handle carefully"
        assert body["id"]

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_shipment_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"shipment-denied-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-denied-tenant-{unique}"
    role_name = f"shipment-denied-role-{unique}"

    tenant, customer, origin, destination = await create_shipment_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=shipment_payload(
                    customer_id=str(customer.id),
                    origin_location_id=str(origin.id),
                    destination_location_id=str(destination.id),
                    tracking_number="DENIED-001",
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
async def test_create_shipment_endpoint_rejects_duplicate_tracking_number() -> None:
    unique = uuid4()

    email = f"shipment-duplicate-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-duplicate-tenant-{unique}"
    role_name = f"shipment-duplicate-role-{unique}"

    tenant, customer, origin, destination = await create_shipment_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=shipment_payload(
                    customer_id=str(customer.id),
                    origin_location_id=str(origin.id),
                    destination_location_id=str(destination.id),
                    tracking_number="SHIP-DUP-001",
                ),
            )

            second_response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=shipment_payload(
                    customer_id=str(customer.id),
                    origin_location_id=str(origin.id),
                    destination_location_id=str(destination.id),
                    tracking_number=" ship-dup-001 ",
                ),
            )

        assert first_response.status_code == 201
        assert second_response.status_code == 409
        assert second_response.json() == {"detail": "Shipment tracking number already exists"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("foreign_resource", "expected_detail"),
    [
        (
            "customer",
            "Shipment customer not found",
        ),
        (
            "origin",
            "Shipment origin location not found",
        ),
        (
            "destination",
            "Shipment destination location not found",
        ),
    ],
)
async def test_create_shipment_endpoint_enforces_resource_tenant_isolation(
    foreign_resource: str,
    expected_detail: str,
) -> None:
    unique = uuid4()

    email = f"shipment-isolation-{unique}@example.com"
    password = "very-secure-shipment-password"

    tenant_slug = f"shipment-isolation-tenant-{unique}"
    foreign_tenant_slug = f"shipment-foreign-tenant-{unique}"
    role_name = f"shipment-isolation-role-{unique}"

    tenant, customer, origin, destination = await create_shipment_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    (
        _,
        foreign_customer,
        foreign_origin,
        foreign_destination,
    ) = await create_foreign_resources(
        tenant_slug=foreign_tenant_slug,
    )

    try:
        customer_id = customer.id
        origin_id = origin.id
        destination_id = destination.id

        if foreign_resource == "customer":
            customer_id = foreign_customer.id

        elif foreign_resource == "origin":
            origin_id = foreign_origin.id

        else:
            destination_id = foreign_destination.id

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=shipment_payload(
                    customer_id=str(customer_id),
                    origin_location_id=str(origin_id),
                    destination_location_id=str(destination_id),
                    tracking_number=f"ISOLATION-{unique}",
                ),
            )

        assert response.status_code == 404
        assert response.json() == {
            "detail": expected_detail,
        }

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
async def test_create_shipment_endpoint_rejects_invalid_weight() -> None:
    unique = uuid4()

    email = f"shipment-weight-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-weight-tenant-{unique}"
    role_name = f"shipment-weight-role-{unique}"

    tenant, customer, origin, destination = await create_shipment_context(
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

        payload = shipment_payload(
            customer_id=str(customer.id),
            origin_location_id=str(origin.id),
            destination_location_id=str(destination.id),
            tracking_number="INVALID-WEIGHT-001",
        )
        payload["weight"] = "0"

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments",
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
