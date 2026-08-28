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


async def create_document_context(
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
                first_name="Document",
                last_name="Manager",
                is_active=True,
            )

            tenant = Tenant(
                name="Documents Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Documents integration role",
            )

            permission = await session.scalar(
                select(Permission).where(
                    Permission.code == Permissions.DOCUMENT_CREATE,
                )
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.DOCUMENT_CREATE,
                    description="Create documents",
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
                name="Document Customer",
                code=f"DOC-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Document Origin",
                code=f"DOC-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Document Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Document Destination",
                code=f"DOC-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Nablus",
                address_line1="Document Destination Address",
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
                tracking_number=f"DOC-SHIP-{uuid4()}",
                weight=Decimal("12.500"),
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
                name="Foreign Documents Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Document Customer",
                code=f"FOREIGN-DOC-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Foreign Document Origin",
                code=f"FOREIGN-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Hebron",
                address_line1="Foreign Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Foreign Document Destination",
                code=f"FOREIGN-DEST-{uuid4()}",
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
                tracking_number=f"FOREIGN-DOC-SHIP-{uuid4()}",
                weight=Decimal("12.500"),
            )

            session.add(shipment)

            await session.commit()

            return tenant, shipment

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


def document_payload() -> dict[str, object]:
    return {
        "document_type": "shipping_label",
        "filename": "  shipping-label.pdf  ",
        "content_type": "  application/pdf  ",
        "storage_key": "  labels/shipping-label.pdf  ",
    }


@pytest.mark.integration
async def test_create_document_endpoint_creates_document() -> None:
    unique = uuid4()

    email = f"document-create-{unique}@example.com"
    password = "very-secure-document-password"
    tenant_slug = f"document-create-tenant-{unique}"
    role_name = f"document-create-role-{unique}"

    tenant, shipment = await create_document_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/documents",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=document_payload(),
            )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["shipment_id"] == str(shipment.id)
        assert body["type"] == "shipping_label"
        assert body["status"] == "pending"
        assert body["filename"] == "shipping-label.pdf"
        assert body["content_type"] == "application/pdf"
        assert body["storage_key"] == "labels/shipping-label.pdf"
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
async def test_create_document_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"document-create-denied-{unique}@example.com"
    password = "very-secure-document-password"
    tenant_slug = f"document-create-denied-tenant-{unique}"
    role_name = f"document-create-denied-role-{unique}"

    tenant, shipment = await create_document_context(
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
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/documents",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=document_payload(),
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
async def test_create_document_endpoint_returns_not_found_for_unknown_shipment() -> None:
    unique = uuid4()

    email = f"document-create-missing-{unique}@example.com"
    password = "very-secure-document-password"
    tenant_slug = f"document-create-missing-tenant-{unique}"
    role_name = f"document-create-missing-role-{unique}"

    tenant, _ = await create_document_context(
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

        missing_shipment_id = uuid4()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{missing_shipment_id}/documents",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=document_payload(),
            )

        assert response.status_code == 404

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_document_endpoint_hides_foreign_shipment() -> None:
    unique = uuid4()

    email = f"document-create-foreign-{unique}@example.com"
    password = "very-secure-document-password"

    tenant_slug = f"document-create-own-tenant-{unique}"
    foreign_tenant_slug = f"document-create-foreign-tenant-{unique}"
    role_name = f"document-create-foreign-role-{unique}"

    tenant, _ = await create_document_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    _, foreign_shipment = await create_foreign_shipment(
        tenant_slug=foreign_tenant_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{foreign_shipment.id}/documents",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=document_payload(),
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
@pytest.mark.parametrize(
    "field",
    [
        "filename",
        "content_type",
        "storage_key",
    ],
)
async def test_create_document_endpoint_rejects_blank_text_fields(
    field: str,
) -> None:
    unique = uuid4()

    email = f"document-create-blank-{unique}@example.com"
    password = "very-secure-document-password"
    tenant_slug = f"document-create-blank-tenant-{unique}"
    role_name = f"document-create-blank-role-{unique}"

    tenant, shipment = await create_document_context(
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

        payload = document_payload()
        payload[field] = "   "

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/shipments/{shipment.id}/documents",
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
