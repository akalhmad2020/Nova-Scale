import asyncio
from uuid import uuid4

import httpx
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
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.role import Role
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.ledger.application.use_cases.bootstrap_accounts import (
    SYSTEM_LEDGER_ACCOUNTS,
)
from app.modules.ledger.infrastructure.models import LedgerAccount


async def cleanup_registration(
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
            user_id = await session.scalar(select(User.id).where(User.email == email))

            tenant_id = await session.scalar(select(Tenant.id).where(Tenant.slug == tenant_slug))

            if user_id is not None:
                await session.execute(delete(Membership).where(Membership.user_id == user_id))

            if tenant_id is not None:
                await session.execute(delete(Membership).where(Membership.tenant_id == tenant_id))

                await session.execute(
                    delete(LedgerAccount).where(LedgerAccount.tenant_id == tenant_id)
                )

            if user_id is not None:
                await session.execute(delete(User).where(User.id == user_id))

            if tenant_id is not None:
                await session.execute(delete(Tenant).where(Tenant.id == tenant_id))

            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.integration
async def test_register_endpoint_onboards_company_atomically() -> None:
    unique = uuid4()

    email = f"api-register-{unique}@example.com"
    tenant_slug = f"api-register-company-{unique}"

    await cleanup_registration(
        email=email,
        tenant_slug=tenant_slug,
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "password": "very-secure-password",
                    "first_name": "API",
                    "last_name": "Owner",
                    "company_name": "API Logistics",
                    "company_slug": tenant_slug,
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body["email"] == email
        assert body["first_name"] == "API"
        assert body["last_name"] == "Owner"
        assert body["company_name"] == "API Logistics"
        assert body["company_slug"] == tenant_slug

        assert body["user_id"]
        assert body["tenant_id"]
        assert body["membership_id"]

        assert "password" not in body
        assert "password_hash" not in body

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
                user = await session.scalar(select(User).where(User.email == email))
                assert user is not None

                tenant = await session.scalar(select(Tenant).where(Tenant.slug == tenant_slug))
                assert tenant is not None

                membership = await session.scalar(
                    select(Membership).where(
                        Membership.tenant_id == tenant.id,
                        Membership.user_id == user.id,
                    )
                )
                assert membership is not None

                owner_role = await session.scalar(select(Role).where(Role.name == "owner"))
                assert owner_role is not None
                assert membership.role_id == owner_role.id

                ledger_accounts = list(
                    await session.scalars(
                        select(LedgerAccount).where(LedgerAccount.tenant_id == tenant.id)
                    )
                )

                assert len(ledger_accounts) == len(SYSTEM_LEDGER_ACCOUNTS)

                assert body["user_id"] == str(user.id)
                assert body["tenant_id"] == str(tenant.id)
                assert body["membership_id"] == str(membership.id)
        finally:
            await engine.dispose()

    finally:
        await cleanup_registration(
            email=email,
            tenant_slug=tenant_slug,
        )


@pytest.mark.integration
async def test_register_endpoint_rejects_duplicate_email() -> None:
    unique = uuid4()

    email = f"api-duplicate-{unique}@example.com"
    first_slug = f"first-company-{unique}"
    second_slug = f"second-company-{unique}"

    try:
        with TestClient(app) as client:
            first_response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "password": "very-secure-password",
                    "first_name": "First",
                    "last_name": "Owner",
                    "company_name": "First Company",
                    "company_slug": first_slug,
                },
            )

            second_response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": email.upper(),
                    "password": "very-secure-password",
                    "first_name": "Second",
                    "last_name": "Owner",
                    "company_name": "Second Company",
                    "company_slug": second_slug,
                },
            )

        assert first_response.status_code == 201
        assert second_response.status_code == 409
        assert second_response.json() == {"detail": "Email is already registered"}

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
                second_tenant = await session.scalar(
                    select(Tenant).where(Tenant.slug == second_slug)
                )

                assert second_tenant is None
        finally:
            await engine.dispose()

    finally:
        await cleanup_registration(
            email=email,
            tenant_slug=first_slug,
        )
        await cleanup_registration(
            email=email,
            tenant_slug=second_slug,
        )


@pytest.mark.integration
async def test_register_endpoint_rejects_duplicate_company_slug() -> None:
    unique = uuid4()

    first_email = f"first-owner-{unique}@example.com"
    second_email = f"second-owner-{unique}@example.com"
    tenant_slug = f"duplicate-company-{unique}"

    try:
        with TestClient(app) as client:
            first_response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": first_email,
                    "password": "very-secure-password",
                    "first_name": "First",
                    "last_name": "Owner",
                    "company_name": "First Company",
                    "company_slug": tenant_slug,
                },
            )

            second_response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": second_email,
                    "password": "very-secure-password",
                    "first_name": "Second",
                    "last_name": "Owner",
                    "company_name": "Second Company",
                    "company_slug": tenant_slug,
                },
            )

        assert first_response.status_code == 201
        assert second_response.status_code == 409
        assert second_response.json() == {"detail": "Tenant slug already exists"}

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
                second_user = await session.scalar(select(User).where(User.email == second_email))

                assert second_user is None
        finally:
            await engine.dispose()

    finally:
        await cleanup_registration(
            email=first_email,
            tenant_slug=tenant_slug,
        )
        await cleanup_registration(
            email=second_email,
            tenant_slug=tenant_slug,
        )


@pytest.mark.integration
async def test_register_endpoint_validates_input() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "short",
                "first_name": "",
                "last_name": "Akram",
                "company_name": "",
                "company_slug": "",
            },
        )

    assert response.status_code == 422


@pytest.mark.integration
async def test_concurrent_registration_allows_only_one_company() -> None:
    unique = uuid4()

    email = f"concurrent-owner-{unique}@example.com"
    tenant_slug = f"concurrent-company-{unique}"

    payload = {
        "email": email,
        "password": "very-secure-password",
        "first_name": "Concurrent",
        "last_name": "Owner",
        "company_name": "Concurrent Company",
        "company_slug": tenant_slug,
    }

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:

            async def register() -> httpx.Response:
                return await client.post(
                    "/api/v1/auth/register",
                    json=payload,
                )

            first_response, second_response = await asyncio.gather(
                register(),
                register(),
            )

        status_codes = sorted(
            [
                first_response.status_code,
                second_response.status_code,
            ]
        )

        assert status_codes == [201, 409]

    finally:
        await cleanup_registration(
            email=email,
            tenant_slug=tenant_slug,
        )
