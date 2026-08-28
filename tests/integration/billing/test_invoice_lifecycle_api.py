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


async def create_lifecycle_context(
    *,
    email: str,
    password: str,
    tenant_slug: str,
    role_name: str,
    permission_codes: tuple[str, ...],
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
                last_name="Lifecycle",
                is_active=True,
            )

            tenant = Tenant(
                name="Billing Lifecycle Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Billing lifecycle integration role",
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
                name="Billing Lifecycle Customer",
                code=f"BILLING-LIFECYCLE-CUST-{uuid4()}",
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

            for permission in permissions:
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
    status: InvoiceStatus = InvoiceStatus.DRAFT,
    with_line: bool = False,
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
            subtotal = Decimal("25.00") if with_line else Decimal("0.00")
            tax_amount = Decimal("5.00")
            total_amount = subtotal + tax_amount

            invoice = Invoice(
                tenant_id=tenant_id,
                customer_id=customer_id,
                invoice_number=invoice_number,
                status=status,
                currency="USD",
                subtotal=subtotal,
                tax_amount=tax_amount,
                total_amount=total_amount,
            )

            if status == InvoiceStatus.ISSUED:
                invoice.issued_at = datetime.now(UTC)

            if status == InvoiceStatus.PAID:
                invoice.issued_at = datetime.now(UTC)
                invoice.paid_at = datetime.now(UTC)

            session.add(invoice)
            await session.flush()

            if with_line:
                session.add(
                    InvoiceLine(
                        tenant_id=tenant_id,
                        invoice_id=invoice.id,
                        shipment_id=None,
                        description="Lifecycle shipping charge",
                        quantity=Decimal("1.0000"),
                        unit_price=Decimal("25.00"),
                        amount=Decimal("25.00"),
                    )
                )

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
                name="Foreign Billing Lifecycle Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Billing Lifecycle Customer",
                code=f"FOREIGN-BILLING-LIFECYCLE-{uuid4()}",
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
                subtotal=Decimal("25.00"),
                tax_amount=Decimal("0.00"),
                total_amount=Decimal("25.00"),
            )

            session.add(invoice)
            await session.flush()

            session.add(
                InvoiceLine(
                    tenant_id=tenant.id,
                    invoice_id=invoice.id,
                    shipment_id=None,
                    description="Foreign lifecycle line",
                    quantity=Decimal("1.0000"),
                    unit_price=Decimal("25.00"),
                    amount=Decimal("25.00"),
                )
            )

            await session.commit()

            return tenant, invoice

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


@pytest.mark.integration
async def test_issue_invoice_endpoint_issues_draft_invoice() -> None:
    unique = uuid4()

    email = f"billing-issue-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-issue-tenant-{unique}"
    role_name = f"billing-issue-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_ISSUE,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-ISSUE-001",
        with_line=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/issue",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(invoice.id)
        assert body["status"] == "issued"
        assert body["issued_at"] is not None
        assert body["paid_at"] is None

        persisted_invoice = await get_invoice(
            invoice_id=invoice.id,
        )

        assert persisted_invoice.status == InvoiceStatus.ISSUED
        assert persisted_invoice.issued_at is not None
        assert persisted_invoice.paid_at is None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_issue_invoice_endpoint_requires_at_least_one_line() -> None:
    unique = uuid4()

    email = f"billing-issue-empty-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-issue-empty-tenant-{unique}"
    role_name = f"billing-issue-empty-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_ISSUE,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-EMPTY-001",
        with_line=False,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/issue",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 409

        persisted_invoice = await get_invoice(
            invoice_id=invoice.id,
        )

        assert persisted_invoice.status == InvoiceStatus.DRAFT
        assert persisted_invoice.issued_at is None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_issue_invoice_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"billing-issue-denied-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-issue-denied-tenant-{unique}"
    role_name = f"billing-issue-denied-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-ISSUE-DENIED-001",
        with_line=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/issue",
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
async def test_mark_invoice_paid_endpoint_marks_issued_invoice_paid() -> None:
    unique = uuid4()

    email = f"billing-paid-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-paid-tenant-{unique}"
    role_name = f"billing-paid-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_MARK_PAID,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-PAID-001",
        status=InvoiceStatus.ISSUED,
        with_line=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/mark-paid",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(invoice.id)
        assert body["status"] == "paid"
        assert body["issued_at"] is not None
        assert body["paid_at"] is not None

        persisted_invoice = await get_invoice(
            invoice_id=invoice.id,
        )

        assert persisted_invoice.status == InvoiceStatus.PAID
        assert persisted_invoice.issued_at is not None
        assert persisted_invoice.paid_at is not None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_mark_invoice_paid_endpoint_rejects_draft_invoice() -> None:
    unique = uuid4()

    email = f"billing-paid-draft-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-paid-draft-tenant-{unique}"
    role_name = f"billing-paid-draft-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_MARK_PAID,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-PAID-DRAFT-001",
        with_line=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/mark-paid",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 409

        persisted_invoice = await get_invoice(
            invoice_id=invoice.id,
        )

        assert persisted_invoice.status == InvoiceStatus.DRAFT
        assert persisted_invoice.paid_at is None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    "initial_status",
    [
        InvoiceStatus.DRAFT,
        InvoiceStatus.ISSUED,
    ],
)
async def test_void_invoice_endpoint_voids_allowed_invoice(
    initial_status: InvoiceStatus,
) -> None:
    unique = uuid4()

    email = f"billing-void-{initial_status.value}-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-void-{initial_status.value}-tenant-{unique}"
    role_name = f"billing-void-{initial_status.value}-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_VOID,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number=f"INV-VOID-{initial_status.value}",
        status=initial_status,
        with_line=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/void",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "void"

        persisted_invoice = await get_invoice(
            invoice_id=invoice.id,
        )

        assert persisted_invoice.status == InvoiceStatus.VOID

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_void_invoice_endpoint_rejects_paid_invoice() -> None:
    unique = uuid4()

    email = f"billing-void-paid-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-void-paid-tenant-{unique}"
    role_name = f"billing-void-paid-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_VOID,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-VOID-PAID-001",
        status=InvoiceStatus.PAID,
        with_line=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/void",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 409

        persisted_invoice = await get_invoice(
            invoice_id=invoice.id,
        )

        assert persisted_invoice.status == InvoiceStatus.PAID

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_issue_invoice_endpoint_rejects_void_invoice() -> None:
    unique = uuid4()

    email = f"billing-issue-void-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-issue-void-tenant-{unique}"
    role_name = f"billing-issue-void-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_ISSUE,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-ISSUE-VOID-001",
        status=InvoiceStatus.VOID,
        with_line=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/issue",
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
async def test_mark_invoice_paid_endpoint_rejects_already_paid_invoice() -> None:
    unique = uuid4()

    email = f"billing-paid-again-{unique}@example.com"
    password = "very-secure-billing-password"
    tenant_slug = f"billing-paid-again-tenant-{unique}"
    role_name = f"billing-paid-again-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_MARK_PAID,),
    )

    invoice = await create_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        invoice_number="INV-PAID-AGAIN-001",
        status=InvoiceStatus.PAID,
        with_line=True,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{invoice.id}/mark-paid",
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
async def test_invoice_lifecycle_endpoint_hides_foreign_invoice() -> None:
    unique = uuid4()

    email = f"billing-lifecycle-foreign-{unique}@example.com"
    password = "very-secure-billing-password"

    tenant_slug = f"billing-lifecycle-own-tenant-{unique}"
    foreign_tenant_slug = f"billing-lifecycle-foreign-tenant-{unique}"
    role_name = f"billing-lifecycle-foreign-role-{unique}"

    tenant, _ = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.INVOICE_ISSUE,),
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
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/invoices/{foreign_invoice.id}/issue",
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
