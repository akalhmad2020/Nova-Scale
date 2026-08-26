from datetime import UTC, datetime
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


async def create_read_context(
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
                last_name="Reader",
                is_active=True,
            )

            tenant = Tenant(
                name="Shipment Read Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Shipment read integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.SHIPMENT_READ)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.SHIPMENT_READ,
                    description="Read shipments",
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
                name="Read Customer",
                code="READ-CUST-001",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Read Origin",
                code="READ-ORIGIN",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Read Destination",
                code="READ-DEST",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Nablus",
                address_line1="Destination Address",
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
                name="Foreign Shipment Read Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Customer",
                code="FOREIGN-CUST",
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


async def create_shipment(
    *,
    tenant_id: UUID,
    customer_id: UUID,
    origin_location_id: UUID,
    destination_location_id: UUID,
    tracking_number: str,
    deleted: bool = False,
) -> Shipment:
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
            shipment = Shipment(
                tenant_id=tenant_id,
                customer_id=customer_id,
                origin_location_id=origin_location_id,
                destination_location_id=destination_location_id,
                tracking_number=tracking_number,
                reference="READ-REF",
                status=ShipmentStatus.DRAFT,
                service_type=ServiceType.STANDARD,
                description="Read integration shipment",
                weight=Decimal("5.000"),
                weight_unit=WeightUnit.KG,
                notes="Read test",
            )

            if deleted:
                shipment.deleted_at = datetime.now(UTC)

            session.add(shipment)
            await session.commit()

            return shipment

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
async def test_list_shipments_endpoint_returns_tenant_shipments() -> None:
    unique = uuid4()

    email = f"shipment-read-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-read-tenant-{unique}"
    role_name = f"shipment-read-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
    ) = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        first = await create_shipment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number="READ-001",
        )

        second = await create_shipment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number="READ-002",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments",
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
async def test_list_shipments_endpoint_excludes_soft_deleted_shipments() -> None:
    unique = uuid4()

    email = f"shipment-read-soft-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-read-soft-{unique}"
    role_name = f"shipment-read-soft-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
    ) = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        active = await create_shipment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number="ACTIVE-001",
        )

        await create_shipment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number="DELETED-001",
            deleted=True,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments",
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
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_shipments_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"shipment-read-denied-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-read-denied-{unique}"
    role_name = f"shipment-read-denied-role-{unique}"

    tenant, _, _, _ = await create_read_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
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
async def test_list_shipments_endpoint_excludes_other_tenant() -> None:
    unique = uuid4()

    email = f"shipment-list-isolation-{unique}@example.com"
    password = "very-secure-shipment-password"

    tenant_slug = f"shipment-list-isolation-{unique}"
    foreign_slug = f"shipment-list-foreign-{unique}"
    role_name = f"shipment-list-isolation-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
    ) = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    (
        foreign_tenant,
        foreign_customer,
        foreign_origin,
        foreign_destination,
    ) = await create_foreign_resources(
        tenant_slug=foreign_slug,
    )

    try:
        own_shipment = await create_shipment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number="OWN-001",
        )

        await create_shipment(
            tenant_id=foreign_tenant.id,
            customer_id=foreign_customer.id,
            origin_location_id=foreign_origin.id,
            destination_location_id=foreign_destination.id,
            tracking_number="FOREIGN-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1
        assert body[0]["id"] == str(own_shipment.id)

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
async def test_get_shipment_endpoint_returns_shipment() -> None:
    unique = uuid4()

    email = f"shipment-detail-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-detail-{unique}"
    role_name = f"shipment-detail-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
    ) = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        shipment = await create_shipment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number="DETAIL-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(shipment.id)
        assert body["tenant_id"] == str(tenant.id)
        assert body["customer_id"] == str(customer.id)
        assert body["origin_location_id"] == str(origin.id)
        assert body["destination_location_id"] == str(destination.id)
        assert body["tracking_number"] == "DETAIL-001"
        assert body["status"] == "draft"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_get_shipment_endpoint_rejects_unknown_shipment() -> None:
    unique = uuid4()

    email = f"shipment-missing-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-missing-{unique}"
    role_name = f"shipment-missing-role-{unique}"

    tenant, _, _, _ = await create_read_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments/{uuid4()}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Shipment not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_get_shipment_endpoint_rejects_other_tenant_shipment() -> None:
    unique = uuid4()

    email = f"shipment-detail-isolation-{unique}@example.com"
    password = "very-secure-shipment-password"

    tenant_slug = f"shipment-detail-isolation-{unique}"
    foreign_slug = f"shipment-detail-foreign-{unique}"
    role_name = f"shipment-detail-isolation-role-{unique}"

    tenant, _, _, _ = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    (
        foreign_tenant,
        foreign_customer,
        foreign_origin,
        foreign_destination,
    ) = await create_foreign_resources(
        tenant_slug=foreign_slug,
    )

    try:
        foreign_shipment = await create_shipment(
            tenant_id=foreign_tenant.id,
            customer_id=foreign_customer.id,
            origin_location_id=foreign_origin.id,
            destination_location_id=foreign_destination.id,
            tracking_number="FOREIGN-DETAIL-001",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments/{foreign_shipment.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
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
async def test_get_shipment_endpoint_rejects_soft_deleted_shipment() -> None:
    unique = uuid4()

    email = f"shipment-detail-deleted-{unique}@example.com"
    password = "very-secure-shipment-password"
    tenant_slug = f"shipment-detail-deleted-{unique}"
    role_name = f"shipment-detail-deleted-role-{unique}"

    (
        tenant,
        customer,
        origin,
        destination,
    ) = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        shipment = await create_shipment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            tracking_number="DELETED-DETAIL-001",
            deleted=True,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Shipment not found"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )
