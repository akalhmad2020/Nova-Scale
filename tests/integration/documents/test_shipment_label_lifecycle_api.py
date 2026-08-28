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
from app.modules.documents.domain.enums import (
    DocumentStatus,
    DocumentType,
    LabelStatus,
)
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
            user_id = await session.scalar(
                select(User.id).where(
                    User.email == email,
                )
            )

            tenant_ids = list(
                (
                    await session.scalars(
                        select(Tenant.id).where(
                            Tenant.slug.in_(tenant_slugs),
                        )
                    )
                ).all()
            )

            role_id = await session.scalar(
                select(Role.id).where(
                    Role.name == role_name,
                )
            )

            if tenant_ids:
                await session.execute(
                    delete(ShipmentLabel).where(
                        ShipmentLabel.tenant_id.in_(tenant_ids),
                    )
                )

                await session.execute(
                    delete(Document).where(
                        Document.tenant_id.in_(tenant_ids),
                    )
                )

                await session.execute(
                    delete(Shipment).where(
                        Shipment.tenant_id.in_(tenant_ids),
                    )
                )

                await session.execute(
                    delete(Customer).where(
                        Customer.tenant_id.in_(tenant_ids),
                    )
                )

                await session.execute(
                    delete(Location).where(
                        Location.tenant_id.in_(tenant_ids),
                    )
                )

            if user_id is not None:
                await session.execute(
                    delete(AuthSession).where(
                        AuthSession.user_id == user_id,
                    )
                )

                await session.execute(
                    delete(Membership).where(
                        Membership.user_id == user_id,
                    )
                )

            if tenant_ids:
                await session.execute(
                    delete(Membership).where(
                        Membership.tenant_id.in_(tenant_ids),
                    )
                )

            if role_id is not None:
                await session.execute(
                    delete(RolePermission).where(
                        RolePermission.role_id == role_id,
                    )
                )

            if user_id is not None:
                await session.execute(
                    delete(User).where(
                        User.id == user_id,
                    )
                )

            if tenant_ids:
                await session.execute(
                    delete(Tenant).where(
                        Tenant.id.in_(tenant_ids),
                    )
                )

            if role_id is not None:
                await session.execute(
                    delete(Role).where(
                        Role.id == role_id,
                    )
                )

            await session.commit()

    finally:
        await engine.dispose()


async def create_lifecycle_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
    permission_codes: tuple[str, ...],
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
                last_name="LabelLifecycle",
                is_active=True,
            )

            tenant = Tenant(
                name="Shipment Label Lifecycle Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Shipment label lifecycle integration role",
            )

            session.add_all(
                [
                    user,
                    tenant,
                    role,
                ]
            )

            await session.flush()

            permissions: list[Permission] = []

            for permission_code in permission_codes:
                permission = await session.scalar(
                    select(Permission).where(
                        Permission.code == permission_code,
                    )
                )

                if permission is None:
                    permission = Permission(
                        code=permission_code,
                        description=f"Integration permission {permission_code}",
                    )
                    session.add(permission)
                    await session.flush()

                permissions.append(permission)

            customer = Customer(
                tenant_id=tenant.id,
                name="Label Lifecycle Customer",
                code=f"LABEL-LIFECYCLE-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Label Lifecycle Origin",
                code=f"LABEL-LIFECYCLE-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Label Lifecycle Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Label Lifecycle Destination",
                code=f"LABEL-LIFECYCLE-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Nablus",
                address_line1="Label Lifecycle Destination Address",
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
                tracking_number=f"LABEL-LIFECYCLE-SHIP-{uuid4()}",
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

            for permission in permissions:
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
                name="Foreign Label Lifecycle Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Lifecycle Customer",
                code=f"FOREIGN-LIFECYCLE-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Foreign Lifecycle Origin",
                code=f"FOREIGN-LIFECYCLE-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Hebron",
                address_line1="Foreign Lifecycle Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Foreign Lifecycle Destination",
                code=f"FOREIGN-LIFECYCLE-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Jenin",
                address_line1="Foreign Lifecycle Destination Address",
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
                tracking_number=f"FOREIGN-LIFECYCLE-SHIP-{uuid4()}",
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


async def create_document(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
    document_type: DocumentType = DocumentType.SHIPPING_LABEL,
    status: DocumentStatus = DocumentStatus.PENDING,
) -> Document:
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

    unique = uuid4()

    try:
        async with session_factory() as session:
            document = Document(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
                type=document_type,
                status=status,
                filename=f"label-{unique}.pdf",
                content_type="application/pdf",
                storage_key=f"labels/{unique}/label.pdf",
            )

            session.add(document)
            await session.commit()

            return document

    finally:
        await engine.dispose()


async def create_shipment_label(
    *,
    tenant_id: UUID,
    shipment_id: UUID,
    status: LabelStatus = LabelStatus.PENDING,
) -> ShipmentLabel:
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
            label = ShipmentLabel(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
                package_id=None,
                carrier_id=None,
                carrier_service_id=None,
                status=status,
                tracking_number=None,
                document_id=None,
            )

            session.add(label)
            await session.commit()

            return label

    finally:
        await engine.dispose()


async def get_document(
    *,
    document_id: UUID,
) -> Document:
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
            document = await session.get(
                Document,
                document_id,
            )

            assert document is not None

            return document

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
async def test_complete_shipment_label_endpoint_generates_label() -> None:
    unique = uuid4()

    email = f"label-complete-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-complete-tenant-{unique}"
    role_name = f"label-complete-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_UPDATE,),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        document = await create_document(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            document_type=DocumentType.SHIPPING_LABEL,
            status=DocumentStatus.PENDING,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/complete",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "document_id": str(document.id),
                    "tracking_number": "  TRACK-12345  ",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(label.id)
        assert body["status"] == "generated"
        assert body["document_id"] == str(document.id)
        assert body["tracking_number"] == "TRACK-12345"

        persisted_document = await get_document(
            document_id=document.id,
        )

        assert persisted_document.status == DocumentStatus.READY

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_complete_shipment_label_endpoint_allows_missing_tracking_number() -> None:
    unique = uuid4()

    email = f"label-complete-no-tracking-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-complete-no-tracking-tenant-{unique}"
    role_name = f"label-complete-no-tracking-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_UPDATE,),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        document = await create_document(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/complete",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "document_id": str(document.id),
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["status"] == "generated"
        assert body["document_id"] == str(document.id)
        assert body["tracking_number"] is None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_complete_shipment_label_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"label-complete-denied-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-complete-denied-tenant-{unique}"
    role_name = f"label-complete-denied-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        document = await create_document(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/complete",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "document_id": str(document.id),
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
async def test_complete_shipment_label_endpoint_rejects_voided_label() -> None:
    unique = uuid4()

    email = f"label-complete-voided-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-complete-voided-tenant-{unique}"
    role_name = f"label-complete-voided-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_UPDATE,),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            status=LabelStatus.VOIDED,
        )

        document = await create_document(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/complete",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "document_id": str(document.id),
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
async def test_complete_shipment_label_endpoint_rejects_document_from_different_shipment() -> None:
    unique = uuid4()

    email = f"label-complete-mismatch-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-complete-mismatch-tenant-{unique}"
    role_name = f"label-complete-mismatch-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_UPDATE,),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

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
                    select(Customer).where(
                        Customer.tenant_id == tenant.id,
                    )
                )

                locations = list(
                    (
                        await session.scalars(
                            select(Location).where(
                                Location.tenant_id == tenant.id,
                            )
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
                    tracking_number=f"SECOND-LIFECYCLE-{uuid4()}",
                    status=ShipmentStatus.DRAFT,
                    service_type=ServiceType.STANDARD,
                    weight=Decimal("10.000"),
                    weight_unit=WeightUnit.KG,
                )

                session.add(second_shipment)
                await session.commit()

        finally:
            await engine.dispose()

        document = await create_document(
            tenant_id=tenant.id,
            shipment_id=second_shipment.id,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/complete",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "document_id": str(document.id),
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
async def test_complete_shipment_label_endpoint_rejects_non_shipping_label_document() -> None:
    unique = uuid4()

    email = f"label-complete-type-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-complete-type-tenant-{unique}"
    role_name = f"label-complete-type-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_UPDATE,),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        document = await create_document(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            document_type=DocumentType.COMMERCIAL_INVOICE,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/complete",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "document_id": str(document.id),
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
async def test_complete_shipment_label_endpoint_hides_foreign_document() -> None:
    unique = uuid4()

    email = f"label-complete-foreign-{unique}@example.com"
    password = "very-secure-label-password"

    tenant_slug = f"label-complete-own-tenant-{unique}"
    foreign_slug = f"label-complete-foreign-tenant-{unique}"
    role_name = f"label-complete-foreign-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_UPDATE,),
    )

    foreign_tenant, foreign_shipment = await create_foreign_shipment(
        tenant_slug=foreign_slug,
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        foreign_document = await create_document(
            tenant_id=foreign_tenant.id,
            shipment_id=foreign_shipment.id,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/complete",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "document_id": str(foreign_document.id),
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
async def test_mark_shipment_label_failed_endpoint_marks_label_failed() -> None:
    unique = uuid4()

    email = f"label-failed-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-failed-tenant-{unique}"
    role_name = f"label-failed-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_UPDATE,),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/failed",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(label.id)
        assert body["status"] == "failed"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_mark_shipment_label_failed_endpoint_rejects_voided_label() -> None:
    unique = uuid4()

    email = f"label-failed-voided-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-failed-voided-tenant-{unique}"
    role_name = f"label-failed-voided-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_UPDATE,),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            status=LabelStatus.VOIDED,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/failed",
                headers={
                    "Authorization": f"Bearer {access_token}",
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
async def test_void_shipment_label_endpoint_voids_label() -> None:
    unique = uuid4()

    email = f"label-void-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-void-tenant-{unique}"
    role_name = f"label-void-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_VOID,),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/void",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(label.id)
        assert body["status"] == "voided"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_void_shipment_label_endpoint_rejects_already_voided_label() -> None:
    unique = uuid4()

    email = f"label-void-again-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-void-again-tenant-{unique}"
    role_name = f"label-void-again-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_VOID,),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            status=LabelStatus.VOIDED,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/void",
                headers={
                    "Authorization": f"Bearer {access_token}",
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
async def test_mark_document_failed_endpoint_marks_document_failed() -> None:
    unique = uuid4()

    email = f"document-failed-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"document-failed-tenant-{unique}"
    role_name = f"document-failed-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.DOCUMENT_UPDATE,),
    )

    try:
        document = await create_document(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            status=DocumentStatus.PENDING,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/documents/{document.id}/failed",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(document.id)
        assert body["status"] == "failed"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_complete_shipment_label_endpoint_rejects_failed_label() -> None:
    unique = uuid4()

    email = f"label-complete-failed-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-complete-failed-tenant-{unique}"
    role_name = f"label-complete-failed-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_UPDATE,),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            status=LabelStatus.FAILED,
        )

        document = await create_document(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/complete",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "document_id": str(document.id),
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
async def test_mark_generated_shipment_label_failed_endpoint_rejects_transition() -> None:
    unique = uuid4()

    email = f"label-generated-failed-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-generated-failed-tenant-{unique}"
    role_name = f"label-generated-failed-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_UPDATE,),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            status=LabelStatus.GENERATED,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/failed",
                headers={
                    "Authorization": f"Bearer {access_token}",
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
async def test_void_failed_shipment_label_endpoint_rejects_transition() -> None:
    unique = uuid4()

    email = f"label-failed-void-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"label-failed-void-tenant-{unique}"
    role_name = f"label-failed-void-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.SHIPMENT_LABEL_VOID,),
    )

    try:
        label = await create_shipment_label(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            status=LabelStatus.FAILED,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipment-labels/{label.id}/void",
                headers={
                    "Authorization": f"Bearer {access_token}",
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
async def test_mark_ready_document_failed_endpoint_rejects_transition() -> None:
    unique = uuid4()

    email = f"document-ready-failed-{unique}@example.com"
    password = "very-secure-label-password"
    tenant_slug = f"document-ready-failed-tenant-{unique}"
    role_name = f"document-ready-failed-role-{unique}"

    tenant, shipment = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.DOCUMENT_UPDATE,),
    )

    try:
        document = await create_document(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            status=DocumentStatus.READY,
        )

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/documents/{document.id}/failed",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 409

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )
