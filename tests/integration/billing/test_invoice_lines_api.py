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
from app.modules.billing.domain.enums import InvoiceStatus
from app.modules.billing.infrastructure.models.invoice import Invoice
from app.modules.billing.infrastructure.models.invoice_line import InvoiceLine
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
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
                    delete(InvoiceLine).where(
                        InvoiceLine.tenant_id.in_(tenant_ids),
                    )
                )

                await session.execute(
                    delete(Invoice).where(
                        Invoice.tenant_id.in_(tenant_ids),
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


async def create_lines_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
    permission_codes: tuple[str, ...],
) -> tuple[Tenant, Customer, Shipment]:
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
                first_name="Billing",
                last_name="Lines",
                is_active=True,
            )

            tenant = Tenant(
                name="Billing Lines Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Billing lines integration role",
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
                name="Billing Lines Customer",
                code=f"BILLING-LINES-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Billing Lines Origin",
                code=f"BILLING-LINES-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Ramallah",
                address_line1="Billing Lines Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Billing Lines Destination",
                code=f"BILLING-LINES-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Nablus",
                address_line1="Billing Lines Destination Address",
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
                tracking_number=f"BILLING-SHIP-{uuid4()}",
                weight=Decimal("10.000"),
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

            return tenant, customer, shipment

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
                name="Foreign Billing Lines Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Billing Lines Customer",
                code=f"FOREIGN-BILLING-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            origin = Location(
                tenant_id=tenant.id,
                name="Foreign Billing Origin",
                code=f"FOREIGN-BILLING-ORIGIN-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Hebron",
                address_line1="Foreign Billing Origin Address",
                status=LocationStatus.ACTIVE,
            )

            destination = Location(
                tenant_id=tenant.id,
                name="Foreign Billing Destination",
                code=f"FOREIGN-BILLING-DEST-{uuid4()}",
                type=LocationType.WAREHOUSE,
                country_code="PS",
                city="Jenin",
                address_line1="Foreign Billing Destination Address",
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
                tracking_number=f"FOREIGN-BILLING-SHIP-{uuid4()}",
                weight=Decimal("10.000"),
            )

            session.add(shipment)

            await session.commit()

            return tenant, shipment

    finally:
        await engine.dispose()


async def create_invoice(
    *,
    tenant_id: UUID,
    customer_id: UUID,
    invoice_number: str,
    tax_amount: Decimal = Decimal("0.00"),
    status: InvoiceStatus = InvoiceStatus.DRAFT,
) -> Invoice:
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
            invoice = Invoice(
                tenant_id=tenant_id,
                customer_id=customer_id,
                invoice_number=invoice_number,
                status=status,
                currency="USD",
                subtotal=Decimal("0.00"),
                tax_amount=tax_amount,
                total_amount=tax_amount,
            )

            session.add(invoice)
            await session.commit()

            return invoice

    finally:
        await engine.dispose()


async def get_invoice(
    *,
    invoice_id: UUID,
) -> Invoice:
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
            invoice = await session.get(
                Invoice,
                invoice_id,
            )

            assert invoice is not None

            return invoice

    finally:
        await engine.dispose()


async def get_invoice_line(
    *,
    invoice_line_id: UUID,
) -> InvoiceLine | None:
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
                InvoiceLine,
                invoice_line_id,
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


def invoice_line_payload(
    *,
    shipment_id: UUID | None = None,
    description: str = "Shipping service",
    quantity: str = "2.5000",
    unit_price: str = "12.34",
) -> dict[str, object]:
    return {
        "shipment_id": str(shipment_id) if shipment_id is not None else None,
        "description": description,
        "quantity": quantity,
        "unit_price": unit_price,
    }


@pytest.mark.integration
async def test_add_invoice_line_endpoint_creates_line_and_recalculates_invoice() -> None:
    unique = uuid4()

    email = f"billing-line-create-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-line-create-tenant-{unique}"
    role_name = f"billing-line-create-role-{unique}"

    tenant, customer, shipment = await create_lines_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_UPDATE,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-LINE-001",
        tax_amount=Decimal("5.00"),
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_line_payload(
                    shipment_id=shipment.id,
                ),
            )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["invoice_id"] == str(invoice.id)
        assert body["shipment_id"] == str(shipment.id)
        assert body["description"] == "Shipping service"
        assert body["quantity"] == "2.5000"
        assert body["unit_price"] == "12.34"
        assert body["amount"] == "30.85"

        persisted_invoice = await get_invoice(
            invoice_id=invoice.id,
        )

        assert persisted_invoice.subtotal == Decimal("30.85")
        assert persisted_invoice.tax_amount == Decimal("5.00")
        assert persisted_invoice.total_amount == Decimal("35.85")

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_add_invoice_line_endpoint_uses_half_up_rounding() -> None:
    unique = uuid4()

    email = f"billing-line-round-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-line-round-tenant-{unique}"
    role_name = f"billing-line-round-role-{unique}"

    tenant, customer, _ = await create_lines_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_UPDATE,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-ROUND-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_line_payload(
                    quantity="1.0050",
                    unit_price="1.00",
                ),
            )

        assert response.status_code == 201
        assert response.json()["amount"] == "1.01"

        persisted_invoice = await get_invoice(
            invoice_id=invoice.id,
        )

        assert persisted_invoice.subtotal == Decimal("1.01")
        assert persisted_invoice.total_amount == Decimal("1.01")

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_add_multiple_invoice_lines_recalculates_subtotal_and_total() -> None:
    unique = uuid4()

    email = f"billing-line-multiple-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-line-multiple-tenant-{unique}"
    role_name = f"billing-line-multiple-role-{unique}"

    tenant, customer, _ = await create_lines_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_UPDATE,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-MULTIPLE-001",
        tax_amount=Decimal("2.50"),
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            first_response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_line_payload(
                    description="First line",
                    quantity="2.0000",
                    unit_price="10.00",
                ),
            )

            second_response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_line_payload(
                    description="Second line",
                    quantity="3.0000",
                    unit_price="5.50",
                ),
            )

        assert first_response.status_code == 201
        assert second_response.status_code == 201

        assert first_response.json()["amount"] == "20.00"
        assert second_response.json()["amount"] == "16.50"

        persisted_invoice = await get_invoice(
            invoice_id=invoice.id,
        )

        assert persisted_invoice.subtotal == Decimal("36.50")
        assert persisted_invoice.tax_amount == Decimal("2.50")
        assert persisted_invoice.total_amount == Decimal("39.00")

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_add_invoice_line_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"billing-line-denied-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-line-denied-tenant-{unique}"
    role_name = f"billing-line-denied-role-{unique}"

    tenant, customer, _ = await create_lines_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-LINE-DENIED-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_line_payload(),
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
async def test_add_invoice_line_endpoint_returns_not_found_for_unknown_invoice() -> None:
    unique = uuid4()

    email = f"billing-line-missing-invoice-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-line-missing-invoice-tenant-{unique}"
    role_name = f"billing-line-missing-invoice-role-{unique}"

    tenant, _, _ = await create_lines_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_UPDATE,),
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{uuid4()}/lines",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_line_payload(),
            )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Invoice not found",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_add_invoice_line_endpoint_returns_not_found_for_unknown_shipment() -> None:
    unique = uuid4()

    email = f"billing-line-missing-shipment-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-line-missing-shipment-tenant-{unique}"
    role_name = f"billing-line-missing-shipment-role-{unique}"

    tenant, customer, _ = await create_lines_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_UPDATE,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-MISSING-SHIP-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_line_payload(
                    shipment_id=uuid4(),
                ),
            )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Shipment not found",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_add_invoice_line_endpoint_hides_foreign_shipment() -> None:
    unique = uuid4()

    email = f"billing-line-foreign-shipment-{unique}@example.com"
    password = "very-secure-billing-password"

    tenant_slug = f"billing-line-own-tenant-{unique}"
    foreign_tenant_slug = f"billing-line-foreign-tenant-{unique}"
    role_name = f"billing-line-foreign-role-{unique}"

    tenant, customer, _ = await create_lines_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_UPDATE,),
    )

    _, foreign_shipment = await create_foreign_shipment(
        tenant_slug=foreign_tenant_slug,
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-FOREIGN-SHIP-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_line_payload(
                    shipment_id=foreign_shipment.id,
                ),
            )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Shipment not found",
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
async def test_add_invoice_line_endpoint_rejects_non_draft_invoice() -> None:
    unique = uuid4()

    email = f"billing-line-issued-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-line-issued-tenant-{unique}"
    role_name = f"billing-line-issued-role-{unique}"

    tenant, customer, _ = await create_lines_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_UPDATE,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-ISSUED-LINE-001",
        status=InvoiceStatus.ISSUED,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_line_payload(),
            )

        assert response.status_code == 409
        assert response.json() == {
            "detail": "Invoice is not editable",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_remove_invoice_line_endpoint_recalculates_invoice() -> None:
    unique = uuid4()

    email = f"billing-line-remove-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-line-remove-tenant-{unique}"
    role_name = f"billing-line-remove-role-{unique}"

    tenant, customer, _ = await create_lines_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_UPDATE,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-REMOVE-001",
        tax_amount=Decimal("5.00"),
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            first_response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_line_payload(
                    description="Keep this line",
                    quantity="2.0000",
                    unit_price="10.00",
                ),
            )

            second_response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_line_payload(
                    description="Remove this line",
                    quantity="3.0000",
                    unit_price="5.00",
                ),
            )

            assert first_response.status_code == 201
            assert second_response.status_code == 201

            removed_line_id = UUID(second_response.json()["id"])

            delete_response = client.delete(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines/{removed_line_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert delete_response.status_code == 204

        persisted_line = await get_invoice_line(
            invoice_line_id=removed_line_id,
        )

        assert persisted_line is None

        persisted_invoice = await get_invoice(
            invoice_id=invoice.id,
        )

        assert persisted_invoice.subtotal == Decimal("20.00")
        assert persisted_invoice.tax_amount == Decimal("5.00")
        assert persisted_invoice.total_amount == Decimal("25.00")

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_remove_invoice_line_endpoint_returns_not_found_for_unknown_line() -> None:
    unique = uuid4()

    email = f"billing-line-remove-missing-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-line-remove-missing-tenant-{unique}"
    role_name = f"billing-line-remove-missing-role-{unique}"

    tenant, customer, _ = await create_lines_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_UPDATE,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-REMOVE-MISSING-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.delete(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines/{uuid4()}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Invoice line not found",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_remove_invoice_line_endpoint_rejects_non_draft_invoice() -> None:
    unique = uuid4()

    email = f"billing-line-remove-issued-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-line-remove-issued-tenant-{unique}"
    role_name = f"billing-line-remove-issued-role-{unique}"

    tenant, customer, _ = await create_lines_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_UPDATE,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-REMOVE-ISSUED-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            create_response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_line_payload(),
            )

        assert create_response.status_code == 201

        invoice_line_id = UUID(create_response.json()["id"])

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
                persisted_invoice = await session.get(
                    Invoice,
                    invoice.id,
                )

                assert persisted_invoice is not None

                persisted_invoice.status = InvoiceStatus.ISSUED

                await session.commit()

        finally:
            await engine.dispose()

        with TestClient(app) as client:
            response = client.delete(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines/{invoice_line_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 409
        assert response.json() == {
            "detail": "Invoice is not editable",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("description", "   "),
        ("quantity", "0"),
        ("quantity", "-1"),
        ("unit_price", "-0.01"),
    ],
)
async def test_add_invoice_line_endpoint_rejects_invalid_input(
    field: str,
    value: str,
) -> None:
    unique = uuid4()

    email = f"billing-line-invalid-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-line-invalid-tenant-{unique}"
    role_name = f"billing-line-invalid-role-{unique}"

    tenant, customer, _ = await create_lines_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_UPDATE,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number=f"INV-INVALID-{unique}",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        payload = invoice_line_payload()
        payload[field] = value

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/lines",
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
