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
                first_name="Payments",
                last_name="Reader",
                is_active=True,
            )

            tenant = Tenant(
                name="Payments Read Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Payments read integration role",
            )

            permission = await session.scalar(
                select(Permission).where(
                    Permission.code == Permissions.PAYMENT_READ,
                )
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.PAYMENT_READ,
                    description="Read payments",
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
                name="Payments Read Customer",
                code=f"PAYMENTS-READ-CUST-{uuid4()}",
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


async def create_payment(
    *,
    tenant_id: UUID,
    customer_id: UUID,
    payment_number: str,
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
            payment = Payment(
                tenant_id=tenant_id,
                customer_id=customer_id,
                payment_number=payment_number,
                status=PaymentStatus.DRAFT,
                currency="USD",
                amount=Decimal("100.00"),
                method=PaymentMethod.BANK_TRANSFER,
                reference=None,
                received_at=None,
                posted_at=None,
            )

            session.add(payment)
            await session.commit()

            return payment

    finally:
        await engine.dispose()


async def create_foreign_payment(
    *,
    tenant_slug: str,
) -> tuple[Tenant, Payment]:
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
                name="Foreign Payments Read Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Payments Read Customer",
                code=f"FOREIGN-PAYMENTS-READ-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            session.add(customer)
            await session.flush()

            payment = Payment(
                tenant_id=tenant.id,
                customer_id=customer.id,
                payment_number=f"FOREIGN-PAY-{uuid4()}",
                status=PaymentStatus.DRAFT,
                currency="USD",
                amount=Decimal("100.00"),
                method=PaymentMethod.CASH,
                reference=None,
                received_at=None,
                posted_at=None,
            )

            session.add(payment)
            await session.commit()

            return tenant, payment

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
async def test_get_payment_endpoint_returns_payment() -> None:
    unique = uuid4()

    email = f"payments-read-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-read-tenant-{unique}"
    role_name = f"payments-read-role-{unique}"

    tenant, customer = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    payment = await create_payment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-READ-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/payments/{payment.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(payment.id)
        assert body["tenant_id"] == str(tenant.id)
        assert body["customer_id"] == str(customer.id)
        assert body["payment_number"] == "PAY-READ-001"
        assert body["status"] == PaymentStatus.DRAFT.value
        assert body["currency"] == "USD"
        assert body["amount"] == "100.00"

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_list_payments_endpoint_returns_tenant_payments() -> None:
    unique = uuid4()

    email = f"payments-list-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-list-tenant-{unique}"
    foreign_tenant_slug = f"payments-list-foreign-{unique}"
    role_name = f"payments-list-role-{unique}"

    tenant, customer = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    first_payment = await create_payment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-LIST-001",
    )

    second_payment = await create_payment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-LIST-002",
    )

    _, foreign_payment = await create_foreign_payment(
        tenant_slug=foreign_tenant_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/payments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 200

        body = response.json()

        payment_ids = {item["id"] for item in body}

        assert str(first_payment.id) in payment_ids
        assert str(second_payment.id) in payment_ids
        assert str(foreign_payment.id) not in payment_ids

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
async def test_get_payment_endpoint_hides_foreign_payment() -> None:
    unique = uuid4()

    email = f"payments-foreign-read-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-foreign-read-tenant-{unique}"
    foreign_tenant_slug = f"payments-foreign-read-other-{unique}"
    role_name = f"payments-foreign-read-role-{unique}"

    tenant, _ = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    _, foreign_payment = await create_foreign_payment(
        tenant_slug=foreign_tenant_slug,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/tenants/{tenant.id}/payments/{foreign_payment.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Payment not found"}

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
async def test_read_payment_endpoints_require_permission() -> None:
    unique = uuid4()

    email = f"payments-read-forbidden-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-read-forbidden-tenant-{unique}"
    role_name = f"payments-read-forbidden-role-{unique}"

    tenant, customer = await create_read_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=False,
    )

    payment = await create_payment(
        tenant_id=tenant.id,
        customer_id=customer.id,
        payment_number="PAY-FORBIDDEN-001",
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            list_response = client.get(
                f"/api/v1/tenants/{tenant.id}/payments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

            get_response = client.get(
                f"/api/v1/tenants/{tenant.id}/payments/{payment.id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        assert list_response.status_code == 403
        assert get_response.status_code == 403

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )
