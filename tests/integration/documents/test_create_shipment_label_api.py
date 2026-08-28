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
from app.modules.carriers.domain.enums import CarrierStatus
from app.modules.carriers.infrastructure.models.carrier import Carrier
from app.modules.carriers.infrastructure.models.carrier_service import CarrierService
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.documents.infrastructure.models.document import Document
from app.modules.documents.infrastructure.models.shipment_label import ShipmentLabel
from app.modules.identity.domain.enums import MembershipStatus, TenantStatus
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.permission import Permission
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.role_permission import RolePermission
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)
from app.modules.locations.domain.enums import LocationStatus, LocationType
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
                await session.execute(
                    delete(ShipmentLabel).where(ShipmentLabel.tenant_id.in_(tenant_ids))
                )
                await session.execute(delete(Document).where(Document.tenant_id.in_(tenant_ids)))
                await session.execute(delete(Package).where(Package.tenant_id.in_(tenant_ids)))
                await session.execute(
                    delete(CarrierService).where(CarrierService.tenant_id.in_(tenant_ids))
                )
                await session.execute(delete(Carrier).where(Carrier.tenant_id.in_(tenant_ids)))
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


async def create_label_context(
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
                first_name="Shipment",
                last_name="LabelManager",
                is_active=True,
            )

            tenant = Tenant(
                name="Shipment Label Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Shipment label integration role",
            )

            permission = await session.scalar(
                select(Permission).where(Permission.code == Permissions.SHIPMENT_LABEL_CREATE)
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.SHIPMENT_LABEL_CREATE,
                    description="Create shipment labels",
                )
                session.add(permission)

            session.add_all([user, tenant, role])
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Label Customer",
                code=f"LABEL-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Label Origin",
                code=f"LABEL-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Label Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Label Destination",
                code=f"LABEL-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Nablus",
                address_line1="Label Destination Address",
                status=LocationStatus.ACTIVE,
            )

            session.add_all([customer, origin, destination])
            await session.flush()

            shipment = Shipment(
                tenant_id=tenant.id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
                tracking_number=f"LABEL-SHIP-{uuid4()}",
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

            return tenant, shipment

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
                name="Foreign Shipment Label Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Label Customer",
                code=f"FOREIGN-LABEL-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Foreign Label Origin",
                code=f"FOREIGN-LABEL-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Hebron",
                address_line1="Foreign Label Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Foreign Label Destination",
                code=f"FOREIGN-LABEL-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Jenin",
                address_line1="Foreign Label Destination Address",
                status=LocationStatus.ACTIVE,
            )

            session.add_all([customer, origin, destination])
            await session.flush()

            shipment = Shipment(
                tenant_id=tenant.id,
                customer_id=customer.id,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
                tracking_number=f"FOREIGN-LABEL-SHIP-{uuid4()}",
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
                weight=Decimal("4.500"),
                weight_unit=WeightUnit.KG,
            )

            session.add(package)
            await session.commit()

            return package

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
                name=f"{code} Service",
                service_type=ServiceType.EXPRESS,
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
async def test_create_shipment_label_endpoint_creates_shipment_level_label() -> None:
    unique = uuid4()

    email = f"label-create-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-create-tenant-{unique}"
    role_name = f"label-create-role-{unique}"

    tenant, shipment = await create_label_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={},
            )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["shipment_id"] == str(shipment.id)
        assert body["package_id"] is None
        assert body["carrier_id"] is None
        assert body["carrier_service_id"] is None
        assert body["status"] == "pending"
        assert body["tracking_number"] is None
        assert body["document_id"] is None
        assert body["id"]
        assert body["created_at"]
        assert body["updated_at"]

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_shipment_label_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"label-denied-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-denied-tenant-{unique}"
    role_name = f"label-denied-role-{unique}"

    tenant, shipment = await create_label_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={},
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
async def test_create_shipment_label_endpoint_returns_not_found_for_unknown_shipment() -> None:
    unique = uuid4()

    email = f"label-missing-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-missing-tenant-{unique}"
    role_name = f"label-missing-role-{unique}"

    tenant, _ = await create_label_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments/{uuid4()}/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={},
            )

        assert response.status_code == 404

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_shipment_label_endpoint_hides_foreign_shipment() -> None:
    unique = uuid4()

    email = f"label-foreign-shipment-{unique}@example.com"
    password = "very-secure-label-password"

    tenant_slug = f"label-own-tenant-{unique}"
    foreign_slug = f"label-foreign-tenant-{unique}"
    role_name = f"label-foreign-role-{unique}"

    tenant, _ = await create_label_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments/{foreign_shipment.id}/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={},
            )

        assert response.status_code == 404

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
async def test_create_shipment_label_endpoint_creates_package_label() -> None:
    unique = uuid4()

    email = f"label-package-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-package-tenant-{unique}"
    role_name = f"label-package-role-{unique}"

    tenant, shipment = await create_label_context(
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
            package_number=f"PKG-{unique}",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "package_id": str(package.id),
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body["shipment_id"] == str(shipment.id)
        assert body["package_id"] == str(package.id)
        assert body["status"] == "pending"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_shipment_label_endpoint_creates_label_with_carrier_service() -> None:
    unique = uuid4()

    email = f"label-carrier-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-carrier-tenant-{unique}"
    role_name = f"label-carrier-role-{unique}"

    tenant, shipment = await create_label_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        carrier = await create_carrier(
            tenant_id=tenant.id,
            code=f"DHL-{str(unique)[:8]}",
        )

        service = await create_carrier_service(
            tenant_id=tenant.id,
            carrier_id=carrier.id,
            code=f"EXP-{str(unique)[:8]}",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "carrier_id": str(carrier.id),
                    "carrier_service_id": str(service.id),
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body["carrier_id"] == str(carrier.id)
        assert body["carrier_service_id"] == str(service.id)
        assert body["status"] == "pending"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_shipment_label_endpoint_rejects_package_from_different_shipment() -> None:
    unique = uuid4()

    email = f"label-package-mismatch-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-package-mismatch-tenant-{unique}"
    role_name = f"label-package-mismatch-role-{unique}"

    tenant, shipment = await create_label_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
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
                customer = await session.scalar(
                    select(Customer).where(Customer.tenant_id == tenant.id)
                )

                locations = list(
                    (
                        await session.scalars(
                            select(Location).where(Location.tenant_id == tenant.id)
                        )
                    ).all()
                )

                assert customer is not None
                assert len(locations) >= 2

                second_shipment = Shipment(
                    tenant_id=tenant.id,
                    customer_id=customer.id,
                    origin_location_id=locations[0].id,
                    destination_location_id=locations[1].id,
                    tracking_number=f"LABEL-SECOND-SHIP-{uuid4()}",
                    status=ShipmentStatus.DRAFT,
                    service_type=ServiceType.STANDARD,
                    weight=Decimal("10.000"),
                    weight_unit=WeightUnit.KG,
                )

                session.add(second_shipment)
                await session.commit()

        finally:
            await engine.dispose()

        package = await create_package(
            tenant_id=tenant.id,
            shipment_id=second_shipment.id,
            package_number=f"MISMATCH-{unique}",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "package_id": str(package.id),
                },
            )

        assert response.status_code == 409

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_shipment_label_endpoint_hides_foreign_package() -> None:
    unique = uuid4()

    email = f"label-foreign-package-{unique}@example.com"
    password = "very-secure-label-password"

    tenant_slug = f"label-package-own-tenant-{unique}"
    foreign_slug = f"label-package-foreign-tenant-{unique}"
    role_name = f"label-foreign-package-role-{unique}"

    tenant, shipment = await create_label_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    foreign_tenant, foreign_shipment = await create_foreign_shipment(
        tenant_slug=foreign_slug,
    )

    try:
        foreign_package = await create_package(
            tenant_id=foreign_tenant.id,
            shipment_id=foreign_shipment.id,
            package_number=f"FOREIGN-{unique}",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "package_id": str(foreign_package.id),
                },
            )

        assert response.status_code == 404

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
async def test_create_shipment_label_endpoint_hides_foreign_carrier() -> None:
    unique = uuid4()

    email = f"label-foreign-carrier-{unique}@example.com"
    password = "very-secure-label-password"

    tenant_slug = f"label-carrier-own-tenant-{unique}"
    foreign_slug = f"label-carrier-foreign-tenant-{unique}"
    role_name = f"label-foreign-carrier-role-{unique}"

    tenant, shipment = await create_label_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    foreign_tenant, _ = await create_foreign_shipment(
        tenant_slug=foreign_slug,
    )

    try:
        foreign_carrier = await create_carrier(
            tenant_id=foreign_tenant.id,
            code=f"FOREIGN-{str(unique)[:8]}",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "carrier_id": str(foreign_carrier.id),
                },
            )

        assert response.status_code == 404

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
async def test_create_shipment_label_endpoint_hides_foreign_carrier_service() -> None:
    unique = uuid4()

    email = f"label-foreign-service-{unique}@example.com"
    password = "very-secure-label-password"

    tenant_slug = f"label-service-own-tenant-{unique}"
    foreign_slug = f"label-service-foreign-tenant-{unique}"
    role_name = f"label-foreign-service-role-{unique}"

    tenant, shipment = await create_label_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    foreign_tenant, _ = await create_foreign_shipment(
        tenant_slug=foreign_slug,
    )

    try:
        foreign_carrier = await create_carrier(
            tenant_id=foreign_tenant.id,
            code=f"FC-{str(unique)[:8]}",
        )

        foreign_service = await create_carrier_service(
            tenant_id=foreign_tenant.id,
            carrier_id=foreign_carrier.id,
            code=f"FS-{str(unique)[:8]}",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "carrier_service_id": str(foreign_service.id),
                },
            )

        assert response.status_code == 404

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
async def test_create_shipment_label_endpoint_rejects_carrier_service_mismatch() -> None:
    unique = uuid4()

    email = f"label-service-mismatch-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-service-mismatch-tenant-{unique}"
    role_name = f"label-service-mismatch-role-{unique}"

    tenant, shipment = await create_label_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        first_carrier = await create_carrier(
            tenant_id=tenant.id,
            code=f"C1-{str(unique)[:8]}",
        )

        second_carrier = await create_carrier(
            tenant_id=tenant.id,
            code=f"C2-{str(unique)[:8]}",
        )

        service = await create_carrier_service(
            tenant_id=tenant.id,
            carrier_id=second_carrier.id,
            code=f"S2-{str(unique)[:8]}",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "carrier_id": str(first_carrier.id),
                    "carrier_service_id": str(service.id),
                },
            )

        assert response.status_code == 409

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_shipment_label_endpoint_allows_service_without_carrier() -> None:
    unique = uuid4()

    email = f"label-service-only-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-service-only-tenant-{unique}"
    role_name = f"label-service-only-role-{unique}"

    tenant, shipment = await create_label_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    try:
        carrier = await create_carrier(
            tenant_id=tenant.id,
            code=f"SC-{str(unique)[:8]}",
        )

        service = await create_carrier_service(
            tenant_id=tenant.id,
            carrier_id=carrier.id,
            code=f"SS-{str(unique)[:8]}",
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "carrier_service_id": str(service.id),
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["shipment_id"] == str(shipment.id)
        assert body["carrier_id"] is None
        assert body["carrier_service_id"] == str(service.id)
        assert body["status"] == "pending"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )
