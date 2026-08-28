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


async def create_invoice_context(
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
                last_name="Manager",
                is_active=True,
            )

            tenant = Tenant(
                name="Billing Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Billing integration role",
            )

            permission = await session.scalar(
                select(Permission).where(
                    Permission.code == Permissions.INVOICE_CREATE,
                )
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.INVOICE_CREATE,
                    description="Create invoices",
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
                name="Billing Customer",
                code=f"BILLING-CUST-{uuid4()}",
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


async def create_foreign_customer(
    *,
    tenant_slug: str,
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

    try:
        async with session_factory() as session:
            tenant = Tenant(
                name="Foreign Billing Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Billing Customer",
                code=f"FOREIGN-BILLING-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            session.add(customer)

            await session.commit()

            return tenant, customer

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


def invoice_payload(
    *,
    customer_id: UUID,
    invoice_number: str = "INV-0001",
) -> dict[str, object]:
    return {
        "customer_id": str(customer_id),
        "invoice_number": invoice_number,
        "currency": "usd",
        "tax_amount": "10.25",
    }


@pytest.mark.integration
async def test_create_invoice_endpoint_creates_invoice() -> None:
    unique = uuid4()

    email = f"billing-create-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-create-tenant-{unique}"
    role_name = f"billing-create-role-{unique}"

    tenant, customer = await create_invoice_context(
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
                f"/api/v1/tenants/{tenant.id}/invoices",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "customer_id": str(customer.id),
                    "invoice_number": "  INV-0001  ",
                    "currency": "usd",
                    "tax_amount": "10.25",
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["customer_id"] == str(customer.id)
        assert body["invoice_number"] == "INV-0001"
        assert body["status"] == "draft"
        assert body["currency"] == "USD"
        assert body["subtotal"] == "0.00"
        assert body["tax_amount"] == "10.25"
        assert body["total_amount"] == "10.25"
        assert body["issued_at"] is None
        assert body["due_at"] is None
        assert body["paid_at"] is None
        assert body["id"]
        assert body["created_at"]
        assert body["updated_at"]

        persisted_invoice = await get_invoice(
            invoice_id=UUID(body["id"]),
        )

        assert persisted_invoice.tenant_id == tenant.id
        assert persisted_invoice.customer_id == customer.id
        assert persisted_invoice.invoice_number == "INV-0001"
        assert persisted_invoice.currency == "USD"
        assert persisted_invoice.subtotal == Decimal("0.00")
        assert persisted_invoice.tax_amount == Decimal("10.25")
        assert persisted_invoice.total_amount == Decimal("10.25")

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_invoice_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"billing-create-denied-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-create-denied-tenant-{unique}"
    role_name = f"billing-create-denied-role-{unique}"

    tenant, customer = await create_invoice_context(
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
                f"/api/v1/tenants/{tenant.id}/invoices",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_payload(
                    customer_id=customer.id,
                ),
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
async def test_create_invoice_endpoint_returns_not_found_for_unknown_customer() -> None:
    unique = uuid4()

    email = f"billing-create-missing-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-create-missing-tenant-{unique}"
    role_name = f"billing-create-missing-role-{unique}"

    tenant, _ = await create_invoice_context(
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
                f"/api/v1/tenants/{tenant.id}/invoices",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_payload(
                    customer_id=uuid4(),
                ),
            )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Customer not found",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_invoice_endpoint_hides_foreign_customer() -> None:
    unique = uuid4()

    email = f"billing-create-foreign-{unique}@example.com"
    password = "very-secure-billing-password"

    tenant_slug = f"billing-create-own-tenant-{unique}"
    foreign_tenant_slug = f"billing-create-foreign-tenant-{unique}"
    role_name = f"billing-create-foreign-role-{unique}"

    tenant, _ = await create_invoice_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    _, foreign_customer = await create_foreign_customer(
        tenant_slug=foreign_tenant_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_payload(
                    customer_id=foreign_customer.id,
                ),
            )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Customer not found",
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
async def test_create_invoice_endpoint_rejects_duplicate_number() -> None:
    unique = uuid4()

    email = f"billing-create-duplicate-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-create-duplicate-tenant-{unique}"
    role_name = f"billing-create-duplicate-role-{unique}"

    tenant, customer = await create_invoice_context(
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
                f"/api/v1/tenants/{tenant.id}/invoices",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_payload(
                    customer_id=customer.id,
                    invoice_number="INV-DUPLICATE-001",
                ),
            )

            second_response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=invoice_payload(
                    customer_id=customer.id,
                    invoice_number="  INV-DUPLICATE-001  ",
                ),
            )

        assert first_response.status_code == 201

        assert second_response.status_code == 409
        assert second_response.json() == {
            "detail": "Invoice number already exists",
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_invoice_endpoint_allows_same_number_in_different_tenants() -> None:
    unique = uuid4()

    first_email = f"billing-number-first-{unique}@example.com"
    second_email = f"billing-number-second-{unique}@example.com"
    password = "very-secure-billing-password"

    first_tenant_slug = f"billing-number-first-tenant-{unique}"
    second_tenant_slug = f"billing-number-second-tenant-{unique}"

    first_role_name = f"billing-number-first-role-{unique}"
    second_role_name = f"billing-number-second-role-{unique}"

    first_tenant, first_customer = await create_invoice_context(
        email=first_email,
        password=password,
        tenant_slug=first_tenant_slug,
        role_name=first_role_name,
        assign_permission=True,
    )

    second_tenant, second_customer = await create_invoice_context(
        email=second_email,
        password=password,
        tenant_slug=second_tenant_slug,
        role_name=second_role_name,
        assign_permission=True,
    )

    try:
        first_access_token = login_and_get_access_token(
            email=first_email,
            password=password,
        )

        second_access_token = login_and_get_access_token(
            email=second_email,
            password=password,
        )

        with TestClient(app) as client:
            first_response = client.post(
                f"/api/v1/tenants/{first_tenant.id}/invoices",
                headers={
                    "Authorization": f"Bearer {first_access_token}",
                },
                json=invoice_payload(
                    customer_id=first_customer.id,
                    invoice_number="INV-SHARED-001",
                ),
            )

            second_response = client.post(
                f"/api/v1/tenants/{second_tenant.id}/invoices",
                headers={
                    "Authorization": f"Bearer {second_access_token}",
                },
                json=invoice_payload(
                    customer_id=second_customer.id,
                    invoice_number="INV-SHARED-001",
                ),
            )

        assert first_response.status_code == 201
        assert second_response.status_code == 201

        assert first_response.json()["invoice_number"] == "INV-SHARED-001"
        assert second_response.json()["invoice_number"] == "INV-SHARED-001"

        assert first_response.json()["tenant_id"] == str(first_tenant.id)
        assert second_response.json()["tenant_id"] == str(second_tenant.id)

    finally:
        await cleanup_test_data(
            email=first_email,
            tenant_slugs=(first_tenant_slug,),
            role_name=first_role_name,
        )

        await cleanup_test_data(
            email=second_email,
            tenant_slugs=(second_tenant_slug,),
            role_name=second_role_name,
        )


@pytest.mark.integration
async def test_create_invoice_endpoint_rejects_negative_tax_amount() -> None:
    unique = uuid4()

    email = f"billing-create-tax-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-create-tax-tenant-{unique}"
    role_name = f"billing-create-tax-role-{unique}"

    tenant, customer = await create_invoice_context(
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

        payload = invoice_payload(
            customer_id=customer.id,
        )
        payload["tax_amount"] = "-0.01"

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices",
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
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("invoice_number", "   "),
        ("currency", "US"),
        ("currency", "USDD"),
    ],
)
async def test_create_invoice_endpoint_rejects_invalid_text_fields(
    field: str,
    value: str,
) -> None:
    unique = uuid4()

    email = f"billing-create-invalid-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-create-invalid-tenant-{unique}"
    role_name = f"billing-create-invalid-role-{unique}"

    tenant, customer = await create_invoice_context(
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

        payload = invoice_payload(
            customer_id=customer.id,
        )
        payload[field] = value

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices",
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
