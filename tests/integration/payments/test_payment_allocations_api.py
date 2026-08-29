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
            user_id = await session.scalar(select(User.id).where(User.email == email))

            tenant_ids = list(
                (
                    await session.scalars(
                        select(Tenant.id).where(
                            Tenant.slug.in_(tenant_slugs),
                        )
                    )
                ).all()
            )

            role_id = await session.scalar(select(Role.id).where(Role.name == role_name))

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
                await session.execute(delete(User).where(User.id == user_id))

            if tenant_ids:
                await session.execute(
                    delete(Tenant).where(
                        Tenant.id.in_(tenant_ids),
                    )
                )

            if role_id is not None:
                await session.execute(delete(Role).where(Role.id == role_id))

            await session.commit()

    finally:
        await engine.dispose()


async def create_allocation_context(
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
                first_name="Payments",
                last_name="Allocation",
                is_active=True,
            )

            tenant = Tenant(
                name="Payments Allocation Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Payments allocation integration role",
            )

            permission = await session.scalar(
                select(Permission).where(
                    Permission.code == Permissions.PAYMENT_UPDATE,
                )
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.PAYMENT_UPDATE,
                    description="Update payment allocations",
                )
                session.add(permission)

            session.add_all([user, tenant, role])
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Payments Allocation Customer",
                code=f"PAYMENTS-ALLOC-CUST-{uuid4()}",
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


async def create_payment_and_invoice(
    *,
    tenant_id: UUID,
    customer_id: UUID,
    payment_number: str,
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
            payment = Payment(
                tenant_id=tenant_id,
                customer_id=customer_id,
                payment_number=payment_number,
                status=payment_status,
                currency="USD",
                amount=Decimal("100.00"),
                method=PaymentMethod.BANK_TRANSFER,
                reference=None,
                received_at=None,
                posted_at=(datetime.now(UTC) if payment_status == PaymentStatus.POSTED else None),
            )

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

            session.add_all([payment, invoice])
            await session.commit()

            return payment, invoice

    finally:
        await engine.dispose()


async def get_allocation(
    *,
    allocation_id: UUID,
) -> PaymentAllocation | None:
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
                PaymentAllocation,
                allocation_id,
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


@pytest.mark.integration
async def test_add_payment_allocation_endpoint_creates_allocation() -> None:
    unique = uuid4()

    email = f"payments-allocation-add-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-allocation-add-tenant-{unique}"
    role_name = f"payments-allocation-add-role-{unique}"

    tenant, customer = await create_allocation_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    payment, invoice = await create_payment_and_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-ALLOC-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/allocations"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "invoice_id": str(invoice.id),
                    "amount": "40.00",
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["payment_id"] == str(payment.id)
        assert body["invoice_id"] == str(invoice.id)
        assert body["amount"] == "40.00"

        allocation = await get_allocation(
            allocation_id=UUID(body["id"]),
        )

        assert allocation is not None
        assert allocation.tenant_id == tenant.id
        assert allocation.payment_id == payment.id
        assert allocation.invoice_id == invoice.id
        assert allocation.amount == Decimal("40.00")

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_remove_payment_allocation_endpoint_deletes_allocation() -> None:
    unique = uuid4()

    email = f"payments-allocation-remove-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-allocation-remove-tenant-{unique}"
    role_name = f"payments-allocation-remove-role-{unique}"

    tenant, customer = await create_allocation_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    payment, invoice = await create_payment_and_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-ALLOC-REMOVE-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            create_response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/allocations"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "invoice_id": str(invoice.id),
                    "amount": "40.00",
                },
            )

            assert create_response.status_code == 201

            allocation_id = UUID(create_response.json()["id"])

            delete_response = client.delete(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/allocations/{allocation_id}"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert delete_response.status_code == 204
        assert delete_response.content == b""

        allocation = await get_allocation(
            allocation_id=allocation_id,
        )

        assert allocation is None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_payment_allocation_endpoints_require_permission() -> None:
    unique = uuid4()

    email = f"payments-allocation-forbidden-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-allocation-forbidden-tenant-{unique}"
    role_name = f"payments-allocation-forbidden-role-{unique}"

    tenant, customer = await create_allocation_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=False,
    )

    payment, invoice = await create_payment_and_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-ALLOC-FORBIDDEN-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            add_response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/allocations"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "invoice_id": str(invoice.id),
                    "amount": "40.00",
                },
            )

            delete_response = client.delete(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/allocations/{uuid4()}"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert add_response.status_code == 403
        assert delete_response.status_code == 403

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_add_payment_allocation_rejects_duplicate_invoice() -> None:
    unique = uuid4()

    email = f"payments-allocation-duplicate-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-allocation-duplicate-tenant-{unique}"
    role_name = f"payments-allocation-duplicate-role-{unique}"

    tenant, customer = await create_allocation_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    payment, invoice = await create_payment_and_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-ALLOC-DUPLICATE-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        url = f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/allocations"

        with TestClient(app) as client:
            first_response = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "invoice_id": str(invoice.id),
                    "amount": "40.00",
                },
            )

            second_response = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "invoice_id": str(invoice.id),
                    "amount": "20.00",
                },
            )

        assert first_response.status_code == 201
        assert second_response.status_code == 409
        assert second_response.json() == {
            "detail": "Payment already has an allocation for this invoice"
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_add_payment_allocation_rejects_draft_invoice() -> None:
    unique = uuid4()

    email = f"payments-allocation-draft-invoice-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-allocation-draft-invoice-tenant-{unique}"
    role_name = f"payments-allocation-draft-invoice-role-{unique}"

    tenant, customer = await create_allocation_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    payment, invoice = await create_payment_and_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-ALLOC-DRAFT-INVOICE-001",
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
            persisted_invoice = await session.get(
                Invoice,
                invoice.id,
            )

            assert persisted_invoice is not None

            persisted_invoice.status = InvoiceStatus.DRAFT
            persisted_invoice.issued_at = None

            await session.commit()

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/allocations"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "invoice_id": str(invoice.id),
                    "amount": "40.00",
                },
            )

        assert response.status_code == 409
        assert response.json() == {"detail": "Invoice is not available for payment"}

    finally:
        await engine.dispose()

        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_add_payment_allocation_rejects_currency_mismatch() -> None:
    unique = uuid4()

    email = f"payments-allocation-currency-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-allocation-currency-tenant-{unique}"
    role_name = f"payments-allocation-currency-role-{unique}"

    tenant, customer = await create_allocation_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    payment, invoice = await create_payment_and_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-ALLOC-CURRENCY-001",
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
            persisted_invoice = await session.get(
                Invoice,
                invoice.id,
            )

            assert persisted_invoice is not None

            persisted_invoice.currency = "EUR"

            await session.commit()

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/allocations"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "invoice_id": str(invoice.id),
                    "amount": "40.00",
                },
            )

        assert response.status_code == 409
        assert response.json() == {"detail": "Payment and invoice currencies do not match"}

    finally:
        await engine.dispose()

        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_add_payment_allocation_rejects_amount_above_payment() -> None:
    unique = uuid4()

    email = f"payments-allocation-payment-cap-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-allocation-payment-cap-tenant-{unique}"
    role_name = f"payments-allocation-payment-cap-role-{unique}"

    tenant, customer = await create_allocation_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    payment, invoice = await create_payment_and_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-ALLOC-PAYMENT-CAP-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/allocations"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "invoice_id": str(invoice.id),
                    "amount": "100.01",
                },
            )

        assert response.status_code == 409
        assert response.json() == {"detail": "Payment allocations exceed payment amount"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_add_payment_allocation_rejects_posted_payment() -> None:
    unique = uuid4()

    email = f"payments-allocation-posted-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-allocation-posted-tenant-{unique}"
    role_name = f"payments-allocation-posted-role-{unique}"

    tenant, customer = await create_allocation_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    payment, invoice = await create_payment_and_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-ALLOC-POSTED-001",
        payment_status=PaymentStatus.POSTED,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/allocations"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "invoice_id": str(invoice.id),
                    "amount": "40.00",
                },
            )

        assert response.status_code == 409
        assert response.json() == {
            "detail": ("Payment allocations can only be modified while payment is draft")
        }

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_add_payment_allocation_rejects_invoice_posted_capacity_exceeded() -> None:
    unique = uuid4()

    email = f"payments-allocation-invoice-cap-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-allocation-invoice-cap-tenant-{unique}"
    role_name = f"payments-allocation-invoice-cap-role-{unique}"

    tenant, customer = await create_allocation_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    payment, invoice = await create_payment_and_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-ALLOC-INVOICE-CAP-001",
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
            posted_payment = Payment(
                tenant_id=tenant.id,
                customer_id=customer.id,
                payment_number="PAY-ALLOC-POSTED-EXISTING-001",
                status=PaymentStatus.POSTED,
                currency="USD",
                amount=Decimal("80.00"),
                method=PaymentMethod.BANK_TRANSFER,
                reference=None,
                received_at=None,
                posted_at=datetime.now(UTC),
            )

            session.add(posted_payment)
            await session.flush()

            session.add(
                PaymentAllocation(
                    tenant_id=tenant.id,
                    payment_id=posted_payment.id,
                    invoice_id=invoice.id,
                    amount=Decimal("80.00"),
                )
            )

            await session.commit()

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/allocations"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "invoice_id": str(invoice.id),
                    "amount": "30.00",
                },
            )

        assert response.status_code == 409
        assert response.json() == {"detail": "Payment allocation exceeds invoice amount"}

    finally:
        await engine.dispose()

        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_remove_payment_allocation_rejects_posted_payment() -> None:
    unique = uuid4()

    email = f"payments-allocation-remove-posted-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-allocation-remove-posted-tenant-{unique}"
    role_name = f"payments-allocation-remove-posted-role-{unique}"

    tenant, customer = await create_allocation_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    payment, invoice = await create_payment_and_invoice(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-ALLOC-REMOVE-POSTED-001",
        payment_status=PaymentStatus.POSTED,
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
            allocation = PaymentAllocation(
                tenant_id=tenant.id,
                payment_id=payment.id,
                invoice_id=invoice.id,
                amount=Decimal("40.00"),
            )

            session.add(allocation)
            await session.commit()

            allocation_id = allocation.id

        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.delete(
                (f"/api/v1/tenants/{tenant.id}/payments/{payment.id}/allocations/{allocation_id}"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 409
        assert response.json() == {
            "detail": ("Payment allocations can only be modified while payment is draft")
        }

        persisted_allocation = await get_allocation(
            allocation_id=allocation_id,
        )

        assert persisted_allocation is not None

    finally:
        await engine.dispose()

        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )
