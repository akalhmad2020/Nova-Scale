import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.main import app
from app.modules.identity.infrastructure.models.user import User


async def _delete_user_by_email(email: str) -> None:
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
            await session.execute(delete(User).where(User.email == email))
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.integration
async def test_register_endpoint_creates_user() -> None:
    email = "api-register@example.com"

    await _delete_user_by_email(email)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "password": "very-secure-password",
                    "first_name": "API",
                    "last_name": "Test",
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body["email"] == email
        assert body["first_name"] == "API"
        assert body["last_name"] == "Test"
        assert body["is_active"] is True

        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body

        assert "password" not in body
        assert "password_hash" not in body
        assert "deleted_at" not in body

    finally:
        await _delete_user_by_email(email)


@pytest.mark.integration
async def test_register_endpoint_rejects_duplicate_email() -> None:
    email = "api-duplicate@example.com"

    await _delete_user_by_email(email)

    payload = {
        "email": email,
        "password": "very-secure-password",
        "first_name": "First",
        "last_name": "User",
    }

    try:
        with TestClient(app) as client:
            first_response = client.post(
                "/api/v1/auth/register",
                json=payload,
            )

            second_response = client.post(
                "/api/v1/auth/register",
                json={
                    **payload,
                    "email": "API-DUPLICATE@EXAMPLE.COM",
                },
            )

        assert first_response.status_code == 201
        assert second_response.status_code == 409
        assert second_response.json() == {"detail": "Email is already registered"}

    finally:
        await _delete_user_by_email(email)


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
            },
        )

    assert response.status_code == 422


@pytest.mark.integration
async def test_concurrent_registration_allows_only_one_user() -> None:
    email = "api-concurrent-register@example.com"

    await _delete_user_by_email(email)

    payload = {
        "email": email,
        "password": "very-secure-password",
        "first_name": "Concurrent",
        "last_name": "User",
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

        conflict_response = first_response if first_response.status_code == 409 else second_response

        assert conflict_response.json() == {"detail": "Email is already registered"}

    finally:
        await _delete_user_by_email(email)
