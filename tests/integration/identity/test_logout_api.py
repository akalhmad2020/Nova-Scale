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
                    first_name="Logout",
                    last_name="API",
                    is_active=True,
                )
            )

            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.integration
async def test_logout_endpoint_revokes_session() -> None:
    email = f"logout-api-{uuid4()}@example.com"
    password = "very-secure-logout-password"

    await create_user(
        email=email,
        password=password,
    )

    try:
        with TestClient(app) as client:
            login_response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": password,
                },
            )

            assert login_response.status_code == 200

            refresh_token = login_response.json()["refresh_token"]

            logout_response = client.post(
                "/api/v1/auth/logout",
                json={
                    "refresh_token": refresh_token,
                },
            )

            assert logout_response.status_code == 204
            assert logout_response.content == b""

            refresh_response = client.post(
                "/api/v1/auth/refresh",
                json={
                    "refresh_token": refresh_token,
                },
            )

        assert refresh_response.status_code == 401
        assert refresh_response.json() == {"detail": "Invalid refresh token"}

    finally:
        await cleanup_user(email)


@pytest.mark.integration
def test_logout_endpoint_rejects_unknown_refresh_token() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/logout",
            json={
                "refresh_token": "unknown-refresh-token",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid refresh token"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.integration
def test_logout_endpoint_validates_request() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/logout",
            json={
                "refresh_token": "",
            },
        )

    assert response.status_code == 422
