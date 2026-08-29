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
from app.modules.payments.domain.enums import PaymentMethod, PaymentStatus
from app.modules.payments.infrastructure.models.payment import Payment
from app.modules.payments.infrastructure.models.payment_allocation import (
    PaymentAllocation,
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
                    delete(PaymentAllocation).where(
                        PaymentAllocation.tenant_id.in_(tenant_ids),
                    )
                )

                await session.execute(
                    delete(Payment).where(
                        Payment.tenant_id.in_(tenant_ids),
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
                first_name="Payments",
                last_name="Lifecycle",
                is_active=True,
            )

            tenant = Tenant(
                name="Payments Lifecycle Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Payments lifecycle integration role",
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
                name="Payments Lifecycle Customer",
                code=f"PAYMENTS-LIFECYCLE-CUST-{uuid4()}",
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


async def create_payment_with_invoice(
    *,
    tenant_id: UUID,
    customer_id: UUID,
    payment_number: str,
    payment_amount: Decimal = Decimal("100.00"),
    allocation_amount: Decimal | None = Decimal("100.00"),
    payment_status: PaymentStatus = PaymentStatus.DRAFT,
) -> tuple[Payment, Invoice]:
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
                invoice_number=f"INV-{uuid4()}",
                status=InvoiceStatus.ISSUED,
                currency="USD",
                subtotal=Decimal("100.00"),
                tax_amount=Decimal("0.00"),
                total_amount=Decimal("100.00"),
                issued_at=datetime.now(UTC),
            )

            payment = Payment(
                tenant_id=tenant_id,
                customer_id=customer_id,
                payment_number=payment_number,
                status=payment_status,
                currency="USD",
                amount=payment_amount,
                method=PaymentMethod.BANK_TRANSFER,
                reference=None,
                received_at=None,
                posted_at=(datetime.now(UTC) if payment_status == PaymentStatus.POSTED else None),
            )

            session.add_all(
                [
                    invoice,
                    payment,
                ]
            )

            await session.flush()

            if allocation_amount is not None:
                session.add(
                    PaymentAllocation(
                        tenant_id=tenant_id,
                        payment_id=payment.id,
                        invoice_id=invoice.id,
                        amount=allocation_amount,
                    )
                )

            await session.commit()

            return payment, invoice

    finally:
        await engine.dispose()


async def get_payment(
    *,
    payment_id: UUID,
) -> Payment:
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
            payment = await session.get(
                Payment,
                payment_id,
            )

            assert payment is not None

            return payment

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
async def test_post_payment_endpoint_posts_draft_payment() -> None:
    unique = uuid4()

    email = f"payments-post-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-post-tenant-{unique}"
    role_name = f"payments-post-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.PAYMENT_POST,),
    )

    payment, _ = await create_payment_with_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-POST-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/post"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(payment.id)
        assert body["status"] == PaymentStatus.POSTED.value
        assert body["posted_at"] is not None

        persisted_payment = await get_payment(
            payment_id=payment.id,
        )

        assert persisted_payment.status == PaymentStatus.POSTED
        assert persisted_payment.posted_at is not None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_void_payment_endpoint_voids_draft_payment() -> None:
    unique = uuid4()

    email = f"payments-void-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-void-tenant-{unique}"
    role_name = f"payments-void-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.PAYMENT_VOID,),
    )

    payment, _ = await create_payment_with_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-VOID-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/void"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(payment.id)
        assert body["status"] == PaymentStatus.VOID.value
        assert body["posted_at"] is None

        persisted_payment = await get_payment(
            payment_id=payment.id,
        )

        assert persisted_payment.status == PaymentStatus.VOID
        assert persisted_payment.posted_at is None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_post_payment_endpoint_rejects_payment_without_allocations() -> None:
    unique = uuid4()

    email = f"payments-post-empty-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-post-empty-tenant-{unique}"
    role_name = f"payments-post-empty-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.PAYMENT_POST,),
    )

    payment, _ = await create_payment_with_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-POST-EMPTY-001",
        allocation_amount=None,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/post"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 409
        assert response.json() == {"detail": "Payment cannot be posted in its current state"}

        persisted_payment = await get_payment(
            payment_id=payment.id,
        )

        assert persisted_payment.status == PaymentStatus.DRAFT
        assert persisted_payment.posted_at is None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_posted_payment_cannot_be_voided() -> None:
    unique = uuid4()

    email = f"payments-posted-void-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-posted-void-tenant-{unique}"
    role_name = f"payments-posted-void-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.PAYMENT_VOID,),
    )

    payment, _ = await create_payment_with_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-POSTED-VOID-001",
        payment_status=PaymentStatus.POSTED,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/void"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 409
        assert response.json() == {"detail": "Payment cannot be voided in its current state"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_payment_lifecycle_endpoints_require_permissions() -> None:
    unique = uuid4()

    email = f"payments-lifecycle-forbidden-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-lifecycle-forbidden-tenant-{unique}"
    role_name = f"payments-lifecycle-forbidden-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(),
    )

    payment, _ = await create_payment_with_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-LIFECYCLE-FORBIDDEN-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            post_response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/post"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

            void_response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/void"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert post_response.status_code == 403
        assert void_response.status_code == 403

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_post_partial_payment_keeps_invoice_issued() -> None:
    unique = uuid4()

    email = f"payments-partial-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-partial-tenant-{unique}"
    role_name = f"payments-partial-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.PAYMENT_POST,),
    )

    payment, invoice = await create_payment_with_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-PARTIAL-001",
        payment_amount=Decimal("40.00"),
        allocation_amount=Decimal("40.00"),
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/post"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == PaymentStatus.POSTED.value

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
                assert persisted_invoice.status == InvoiceStatus.ISSUED
                assert persisted_invoice.paid_at is None

        finally:
            await engine.dispose()

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_post_final_payment_marks_invoice_paid() -> None:
    unique = uuid4()

    email = f"payments-final-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-final-tenant-{unique}"
    role_name = f"payments-final-role-{unique}"

    tenant, customer = await create_lifecycle_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        permission_codes=(Permissions.PAYMENT_POST,),
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
            invoice = Invoice(
                tenant_id=tenant.id,
                customer_id=customer.id,
                invoice_number=f"INV-FINAL-{uuid4()}",
                status=InvoiceStatus.ISSUED,
                currency="USD",
                subtotal=Decimal("100.00"),
                tax_amount=Decimal("0.00"),
                total_amount=Decimal("100.00"),
                issued_at=datetime.now(UTC),
            )

            first_payment = Payment(
                tenant_id=tenant.id,
                customer_id=customer.id,
                payment_number="PAY-FINAL-FIRST-001",
                status=PaymentStatus.POSTED,
                currency="USD",
                amount=Decimal("40.00"),
                method=PaymentMethod.BANK_TRANSFER,
                reference=None,
                received_at=None,
                posted_at=datetime.now(UTC),
            )

            second_payment = Payment(
                tenant_id=tenant.id,
                customer_id=customer.id,
                payment_number="PAY-FINAL-SECOND-001",
                status=PaymentStatus.DRAFT,
                currency="USD",
                amount=Decimal("60.00"),
                method=PaymentMethod.BANK_TRANSFER,
                reference=None,
                received_at=None,
                posted_at=None,
            )

            session.add_all(
                [
                    invoice,
                    first_payment,
                    second_payment,
                ]
            )

            await session.flush()

            session.add_all(
                [
                    PaymentAllocation(
                        tenant_id=tenant.id,
                        payment_id=first_payment.id,
                        invoice_id=invoice.id,
                        amount=Decimal("40.00"),
                    ),
                    PaymentAllocation(
                        tenant_id=tenant.id,
                        payment_id=second_payment.id,
                        invoice_id=invoice.id,
                        amount=Decimal("60.00"),
                    ),
                ]
            )

            await session.commit()

            invoice_id = invoice.id
            second_payment_id = second_payment.id

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{second_payment_id}/post"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(second_payment_id)
        assert body["status"] == PaymentStatus.POSTED.value
        assert body["posted_at"] is not None

        async with session_factory() as session:
            persisted_invoice = await session.get(
                Invoice,
                invoice_id,
            )

            persisted_second_payment = await session.get(
                Payment,
                second_payment_id,
            )

            assert persisted_invoice is not None
            assert persisted_second_payment is not None

            assert persisted_second_payment.status == PaymentStatus.POSTED

            assert persisted_invoice.status == InvoiceStatus.PAID
            assert persisted_invoice.paid_at is not None

    finally:
        await engine.dispose()

        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )
