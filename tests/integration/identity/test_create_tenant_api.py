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
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)
from app.modules.ledger.domain.enums import (
    LedgerAccountPurpose,
    LedgerAccountStatus,
    LedgerAccountType,
)
from app.modules.ledger.infrastructure.models import LedgerAccount


async def cleanup_user_and_tenant(
    *,
    email: str,
    tenant_slug: str,
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

            tenant_id = await session.scalar(
                select(Tenant.id).where(
                    Tenant.slug == tenant_slug,
                )
            )

            if user_id is not None:
                await session.execute(
                    delete(AuthSession).where(
                        AuthSession.user_id == user_id,
                    )
                )

            if user_id is not None:
                await session.execute(
                    delete(Membership).where(
                        Membership.user_id == user_id,
                    )
                )

            if tenant_id is not None:
                await session.execute(
                    delete(Membership).where(
                        Membership.tenant_id == tenant_id,
                    )
                )

                await session.execute(
                    delete(LedgerAccount).where(
                        LedgerAccount.tenant_id == tenant_id,
                    )
                )

            if user_id is not None:
                await session.execute(
                    delete(User).where(
                        User.id == user_id,
                    )
                )

            if tenant_id is not None:
                await session.execute(
                    delete(Tenant).where(
                        Tenant.id == tenant_id,
                    )
                )

            await session.commit()

    finally:
        await engine.dispose()


async def create_user(
    *,
    email: str,
    password: str,
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

    password_hasher = Argon2PasswordHasher()

    try:
        async with session_factory() as session:
            session.add(
                User(
                    email=email,
                    password_hash=password_hasher.hash(password),
                    first_name="Tenant",
                    last_name="Creator",
                    is_active=True,
                )
            )

            await session.commit()

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
async def test_create_tenant_endpoint_creates_owner_membership_and_ledger_accounts() -> None:
    unique = uuid4()

    email = f"tenant-create-{unique}@example.com"
    password = "very-secure-tenant-password"
    tenant_slug = f"acme-logistics-{unique}"

    await create_user(
        email=email,
        password=password,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/tenants",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "Acme Logistics",
                    "slug": tenant_slug,
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body["name"] == "Acme Logistics"
        assert body["slug"] == tenant_slug
        assert body["id"]
        assert body["membership_id"]

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
                tenant = await session.scalar(
                    select(Tenant).where(
                        Tenant.slug == tenant_slug,
                    )
                )

                assert tenant is not None

                membership = await session.scalar(
                    select(Membership).where(
                        Membership.tenant_id == tenant.id,
                    )
                )

                assert membership is not None

                user = await session.scalar(
                    select(User).where(
                        User.email == email,
                    )
                )

                assert user is not None
                assert membership.user_id == user.id

                owner_role = await session.scalar(
                    select(Role).where(
                        Role.name == "owner",
                    )
                )

                assert owner_role is not None
                assert membership.role_id == owner_role.id

                ledger_accounts = list(
                    await session.scalars(
                        select(LedgerAccount)
                        .where(
                            LedgerAccount.tenant_id == tenant.id,
                        )
                        .order_by(LedgerAccount.code)
                    )
                )

                assert len(ledger_accounts) == 4

                assert [account.code for account in ledger_accounts] == [
                    "1000",
                    "1100",
                    "2100",
                    "4000",
                ]

                by_purpose = {account.purpose: account for account in ledger_accounts}

                cash = by_purpose[LedgerAccountPurpose.CASH.value]

                assert cash.name == "Cash"
                assert cash.type == LedgerAccountType.ASSET.value
                assert cash.status == LedgerAccountStatus.ACTIVE.value

                accounts_receivable = by_purpose[LedgerAccountPurpose.ACCOUNTS_RECEIVABLE.value]

                assert accounts_receivable.name == "Accounts Receivable"
                assert accounts_receivable.type == LedgerAccountType.ASSET.value
                assert accounts_receivable.status == LedgerAccountStatus.ACTIVE.value

                tax_payable = by_purpose[LedgerAccountPurpose.TAX_PAYABLE.value]

                assert tax_payable.name == "Tax Payable"
                assert tax_payable.type == LedgerAccountType.LIABILITY.value
                assert tax_payable.status == LedgerAccountStatus.ACTIVE.value

                revenue = by_purpose[LedgerAccountPurpose.REVENUE.value]

                assert revenue.name == "Revenue"
                assert revenue.type == LedgerAccountType.REVENUE.value
                assert revenue.status == LedgerAccountStatus.ACTIVE.value

                assert {account.tenant_id for account in ledger_accounts} == {tenant.id}

        finally:
            await engine.dispose()

    finally:
        await cleanup_user_and_tenant(
            email=email,
            tenant_slug=tenant_slug,
        )


@pytest.mark.integration
async def test_create_tenant_endpoint_rejects_duplicate_slug() -> None:
    unique = uuid4()

    email = f"tenant-duplicate-{unique}@example.com"
    password = "very-secure-tenant-password"
    tenant_slug = f"duplicate-tenant-{unique}"

    await create_user(
        email=email,
        password=password,
    )

    try:
        access_token = login_and_get_access_token(
            email=email,
            password=password,
        )

        with TestClient(app) as client:
            first_response = client.post(
                "/api/v1/tenants",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "First Tenant",
                    "slug": tenant_slug,
                },
            )

            second_response = client.post(
                "/api/v1/tenants",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "Duplicate Tenant",
                    "slug": tenant_slug,
                },
            )

        assert first_response.status_code == 201

        assert second_response.status_code == 409
        assert second_response.json() == {
            "detail": "Tenant slug already exists",
        }

    finally:
        await cleanup_user_and_tenant(
            email=email,
            tenant_slug=tenant_slug,
        )


@pytest.mark.integration
def test_create_tenant_endpoint_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/tenants",
            json={
                "name": "Anonymous Tenant",
                "slug": f"anonymous-{uuid4()}",
            },
        )

    assert response.status_code == 401
