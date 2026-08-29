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


async def create_payment_context(
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
                last_name="Manager",
                is_active=True,
            )

            tenant = Tenant(
                name="Payments Integration Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            role = Role(
                name=role_name,
                description="Payments integration role",
            )

            permission = await session.scalar(
                select(Permission).where(
                    Permission.code == Permissions.PAYMENT_CREATE,
                )
            )

            if permission is None:
                permission = Permission(
                    code=Permissions.PAYMENT_CREATE,
                    description="Create payments",
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
                name="Payments Customer",
                code=f"PAYMENTS-CUST-{uuid4()}",
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
                name="Foreign Payments Tenant",
                slug=tenant_slug,
                status=TenantStatus.ACTIVE,
            )

            session.add(tenant)
            await session.flush()

            customer = Customer(
                tenant_id=tenant.id,
                name="Foreign Payments Customer",
                code=f"FOREIGN-PAYMENTS-CUST-{uuid4()}",
                status=CustomerStatus.ACTIVE,
            )

            session.add(customer)

            await session.commit()

            return tenant, customer

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


def payment_payload(
    *,
    customer_id: UUID,
    payment_number: str = "PAY-0001",
) -> dict[str, object]:
    return {
        "customer_id": str(customer_id),
        "payment_number": payment_number,
        "currency": "USD",
        "amount": "100.00",
        "method": PaymentMethod.BANK_TRANSFER.value,
        "reference": "BANK-REF-001",
    }


@pytest.mark.integration
async def test_create_payment_endpoint_creates_payment() -> None:
    unique = uuid4()

    email = f"payments-create-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-create-tenant-{unique}"
    role_name = f"payments-create-role-{unique}"

    tenant, customer = await create_payment_context(
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
                f"/api/v1/tenants/{tenant.id}/payments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "customer_id": str(customer.id),
                    "payment_number": "  PAY-0001  ",
                    "currency": "USD",
                    "amount": "100.00",
                    "method": "bank_transfer",
                    "reference": "BANK-REF-001",
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body["tenant_id"] == str(tenant.id)
        assert body["customer_id"] == str(customer.id)
        assert body["payment_number"] == "PAY-0001"
        assert body["status"] == PaymentStatus.DRAFT.value
        assert body["currency"] == "USD"
        assert body["amount"] == "100.00"
        assert body["method"] == PaymentMethod.BANK_TRANSFER.value
        assert body["reference"] == "BANK-REF-001"
        assert body["posted_at"] is None

        persisted_payment = await get_payment(
            payment_id=UUID(body["id"]),
        )

        assert persisted_payment.tenant_id == tenant.id
        assert persisted_payment.customer_id == customer.id
        assert persisted_payment.payment_number == "PAY-0001"
        assert persisted_payment.status == PaymentStatus.DRAFT
        assert persisted_payment.amount == 100
        assert persisted_payment.posted_at is None

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_payment_endpoint_rejects_duplicate_payment_number() -> None:
    unique = uuid4()

    email = f"payments-duplicate-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-duplicate-tenant-{unique}"
    role_name = f"payments-duplicate-role-{unique}"

    tenant, customer = await create_payment_context(
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
                f"/api/v1/tenants/{tenant.id}/payments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=payment_payload(
                    customer_id=customer.id,
                    payment_number="PAY-DUPLICATE-001",
                ),
            )

            second_response = client.post(
                f"/api/v1/tenants/{tenant.id}/payments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=payment_payload(
                    customer_id=customer.id,
                    payment_number="PAY-DUPLICATE-001",
                ),
            )

        assert first_response.status_code == 201
        assert second_response.status_code == 409
        assert second_response.json() == {"detail": "Payment number already exists"}

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_payment_endpoint_rejects_foreign_customer() -> None:
    unique = uuid4()

    email = f"payments-foreign-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-foreign-tenant-{unique}"
    foreign_tenant_slug = f"payments-foreign-other-tenant-{unique}"
    role_name = f"payments-foreign-role-{unique}"

    tenant, _ = await create_payment_context(
        email=email,
        password=password,
        tenant_slug=tenant_slug,
        role_name=role_name,
        assign_permission=True,
    )

    foreign_tenant, foreign_customer = await create_foreign_customer(
        tenant_slug=foreign_tenant_slug,
    )

    del foreign_tenant

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/tenants/{tenant.id}/payments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=payment_payload(
                    customer_id=foreign_customer.id,
                ),
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Customer not found"}

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
async def test_create_payment_endpoint_requires_permission() -> None:
    unique = uuid4()

    email = f"payments-no-permission-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-no-permission-tenant-{unique}"
    role_name = f"payments-no-permission-role-{unique}"

    tenant, customer = await create_payment_context(
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
                f"/api/v1/tenants/{tenant.id}/payments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=payment_payload(
                    customer_id=customer.id,
                ),
            )

        assert response.status_code == 403

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )


@pytest.mark.integration
async def test_create_payment_endpoint_rejects_invalid_amount() -> None:
    unique = uuid4()

    email = f"payments-invalid-{unique}@example.com"
    password = "very-secure-payments-password"
    tenant_slug = f"payments-invalid-tenant-{unique}"
    role_name = f"payments-invalid-role-{unique}"

    tenant, customer = await create_payment_context(
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
                f"/api/v1/tenants/{tenant.id}/payments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "customer_id": str(customer.id),
                    "payment_number": "PAY-INVALID-001",
                    "currency": "USD",
                    "amount": "0.00",
                    "method": "cash",
                },
            )

        assert response.status_code == 422

    finally:
        await cleanup_test_data(
            email=email,
            tenant_slugs=(tenant_slug,),
            role_name=role_name,
        )
