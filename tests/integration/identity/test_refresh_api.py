import asyncio
from typing import cast
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
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)


async def cleanup_user(email: str) -> None:
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

            if user_id is not None:
                await session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))

                await session.execute(delete(User).where(User.id == user_id))

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
                    first_name="Refresh",
                    last_name="API",
                    is_active=True,
                )
            )

            await session.commit()
    finally:
        await engine.dispose()


def login(
    client: TestClient,
    *,
    email: str,
    password: str,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    return cast(
        dict[str, object],
        response.json(),
    )


@pytest.mark.integration
async def test_refresh_endpoint_returns_rotated_tokens() -> None:
    email = f"refresh-api-{uuid4()}@example.com"
    password = "very-secure-refresh-password"

    await create_user(
        email=email,
        password=password,
    )

    try:
        with TestClient(app) as client:
            login_body = login(
                client,
                email=email,
                password=password,
            )

            old_refresh_token = login_body["refresh_token"]

            assert isinstance(old_refresh_token, str)

            response = client.post(
                "/api/v1/auth/refresh",
                json={
                    "refresh_token": old_refresh_token,
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["access_token"]
        assert body["refresh_token"]
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 900

        assert body["refresh_token"] != old_refresh_token

    finally:
        await cleanup_user(email)


@pytest.mark.integration
async def test_refresh_endpoint_rejects_old_token_after_rotation() -> None:
    email = f"refresh-reuse-api-{uuid4()}@example.com"
    password = "very-secure-refresh-password"

    await create_user(
        email=email,
        password=password,
    )

    try:
        with TestClient(app) as client:
            login_body = login(
                client,
                email=email,
                password=password,
            )

            old_refresh_token = login_body["refresh_token"]

            assert isinstance(old_refresh_token, str)

            first_refresh_response = client.post(
                "/api/v1/auth/refresh",
                json={
                    "refresh_token": old_refresh_token,
                },
            )

            assert first_refresh_response.status_code == 200

            second_refresh_response = client.post(
                "/api/v1/auth/refresh",
                json={
                    "refresh_token": old_refresh_token,
                },
            )

        assert second_refresh_response.status_code == 401
        assert second_refresh_response.json() == {"detail": "Invalid refresh token"}
        assert second_refresh_response.headers["www-authenticate"] == "Bearer"

    finally:
        await cleanup_user(email)


@pytest.mark.integration
async def test_refresh_endpoint_accepts_new_token_after_rotation() -> None:
    email = f"refresh-chain-api-{uuid4()}@example.com"
    password = "very-secure-refresh-password"

    await create_user(
        email=email,
        password=password,
    )

    try:
        with TestClient(app) as client:
            login_body = login(
                client,
                email=email,
                password=password,
            )

            original_refresh_token = login_body["refresh_token"]

            assert isinstance(original_refresh_token, str)

            first_refresh_response = client.post(
                "/api/v1/auth/refresh",
                json={
                    "refresh_token": original_refresh_token,
                },
            )

            assert first_refresh_response.status_code == 200

            first_refresh_body = first_refresh_response.json()
            rotated_refresh_token = first_refresh_body["refresh_token"]

            assert isinstance(rotated_refresh_token, str)
            assert rotated_refresh_token != original_refresh_token

            second_refresh_response = client.post(
                "/api/v1/auth/refresh",
                json={
                    "refresh_token": rotated_refresh_token,
                },
            )

        assert second_refresh_response.status_code == 200

        second_refresh_body = second_refresh_response.json()

        assert second_refresh_body["access_token"]
        assert second_refresh_body["refresh_token"]
        assert second_refresh_body["token_type"] == "bearer"

        assert second_refresh_body["refresh_token"] != rotated_refresh_token

    finally:
        await cleanup_user(email)


@pytest.mark.integration
def test_refresh_endpoint_rejects_unknown_token() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "this-refresh-token-does-not-exist",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid refresh token"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.integration
def test_refresh_endpoint_validates_request() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "",
            },
        )

    assert response.status_code == 422


@pytest.mark.integration
async def test_concurrent_refresh_allows_only_one_request() -> None:
    email = f"refresh-concurrent-{uuid4()}@example.com"
    password = "very-secure-refresh-password"

    await create_user(
        email=email,
        password=password,
    )

    try:
        with TestClient(app) as sync_client:
            login_body = login(
                sync_client,
                email=email,
                password=password,
            )

        refresh_token = login_body["refresh_token"]

        assert isinstance(refresh_token, str)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as async_client:

            async def refresh() -> httpx.Response:
                return await async_client.post(
                    "/api/v1/auth/refresh",
                    json={
                        "refresh_token": refresh_token,
                    },
                )

            first_response, second_response = await asyncio.gather(
                refresh(),
                refresh(),
            )

        status_codes = sorted(
            [
                first_response.status_code,
                second_response.status_code,
            ]
        )

        assert status_codes == [200, 401]

        failed_response = first_response if first_response.status_code == 401 else second_response

        assert failed_response.json() == {"detail": "Invalid refresh token"}
        assert failed_response.headers["www-authenticate"] == "Bearer"

    finally:
        await cleanup_user(email)
