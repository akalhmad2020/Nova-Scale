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
                    delete(Customer).where(
                        Customer.tenant_id.in_(tenant_ids),
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


async def create_read_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
    assign_permission: bool,
) -> tuple[Tenant, Customer]:
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
                last_name="Reader",
                is_active=True,
            )

            tenant = Tenant(
                name="Billing Read Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Billing read integration role",
            )

            permission = await session.scalar(
                select(Permission).where(
                    Permission.code == Permissions.INVOICE_READ,
                )
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.INVOICE_READ,
                    description="Read invoices",
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
                name="Billing Read Customer",
                code=f"BILLING-READ-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            session.add(customer)

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

            return tenant, customer

    finally:
        await engine.dispose()


async def create_invoice(
    *,
    tenant_id: UUID,
    customer_id: UUID,
    invoice_number: str,
    tax_amount: Decimal = Decimal("0.00"),
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
                status=InvoiceStatus.DRAFT,
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


async def create_foreign_invoice(
    *,
    tenant_slug: str,
) -> tuple[Tenant, Invoice]:
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
                name="Foreign Billing Read Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Billing Read Customer",
                code=f"FOREIGN-BILLING-READ-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            session.add(customer)
            await session.flush()

            invoice = Invoice(
                tenant_id=tenant.id,
                customer_id=customer.id,
                invoice_number=f"FOREIGN-INV-{uuid4()}",
                status=InvoiceStatus.DRAFT,
                currency="USD",
                subtotal=Decimal("0.00"),
                tax_amount=Decimal("0.00"),
                total_amount=Decimal("0.00"),
            )

            session.add(invoice)
            await session.commit()

            return tenant, invoice

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
async def test_get_invoice_endpoint_returns_invoice() -> None:
    unique = uuid4()

    email = f"billing-read-get-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-read-get-tenant-{unique}"
    role_name = f"billing-read-get-role-{unique}"

    tenant, customer = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-READ-001",
        tax_amount=Decimal("4.50"),
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(invoice.id)
        assert body["tenant_id"] == str(tenant.id)
        assert body["customer_id"] == str(customer.id)
        assert body["invoice_number"] == "INV-READ-001"
        assert body["status"] == "draft"
        assert body["currency"] == "USD"
        assert body["subtotal"] == "0.00"
        assert body["tax_amount"] == "4.50"
        assert body["total_amount"] == "4.50"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_get_invoice_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"billing-read-denied-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-read-denied-tenant-{unique}"
    role_name = f"billing-read-denied-role-{unique}"

    tenant, customer = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=False,
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-READ-DENIED-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}",
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
async def test_get_invoice_endpoint_returns_not_found_for_unknown_invoice() -> None:
    unique = uuid4()

    email = f"billing-read-missing-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-read-missing-tenant-{unique}"
    role_name = f"billing-read-missing-role-{unique}"

    tenant, _ = await create_read_context(
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
                f"/api/v1/tenants/{tenant.id}/invoices/{uuid4()}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
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
async def test_get_invoice_endpoint_hides_foreign_invoice() -> None:
    unique = uuid4()

    email = f"billing-read-foreign-{unique}@example.com"
    password = "very-secure-billing-password"

    tenant_slug = f"billing-read-own-tenant-{unique}"
    foreign_tenant_slug = f"billing-read-foreign-tenant-{unique}"
    role_name = f"billing-read-foreign-role-{unique}"

    tenant, _ = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    _, foreign_invoice = await create_foreign_invoice(
        tenant_slug=foreign_tenant_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/invoices/{foreign_invoice.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Invoice not found",
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
async def test_list_invoices_endpoint_returns_only_current_tenant_invoices() -> None:
    unique = uuid4()

    email = f"billing-read-list-{unique}@example.com"
    password = "very-secure-billing-password"

    tenant_slug = f"billing-read-list-tenant-{unique}"
    foreign_tenant_slug = f"billing-read-list-foreign-tenant-{unique}"
    role_name = f"billing-read-list-role-{unique}"

    tenant, customer = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    first_invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-LIST-001",
    )

    second_invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-LIST-002",
    )

    _, foreign_invoice = await create_foreign_invoice(
        tenant_slug=foreign_tenant_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/invoices",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert isinstance(body, list)
        assert len(body) == 2

        invoice_ids = {item["id"] for item in body}

        assert str(first_invoice.id) in invoice_ids
        assert str(second_invoice.id) in invoice_ids
        assert str(foreign_invoice.id) not in invoice_ids

        assert all(item["tenant_id"] == str(tenant.id) for item in body)

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
async def test_list_invoices_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"billing-read-list-denied-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-read-list-denied-tenant-{unique}"
    role_name = f"billing-read-list-denied-role-{unique}"

    tenant, customer = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=False,
    )

    await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-LIST-DENIED-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/invoices",
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
