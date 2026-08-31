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
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)


async def _cleanup_user(email: str) -> None:
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
            user = await session.scalar(
                User.__table__.select().with_only_columns(User.id).where(User.email == email)
            )

            if user is not None:
                await session.execute(delete(AuthSession).where(AuthSession.user_id == user))

            await session.execute(delete(User).where(User.email == email))

            await session.commit()
    finally:
        await engine.dispose()


async def _create_user(
    *,
    email: str,
    password: str,
    is_active: bool = True,
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

    hasher = Argon2PasswordHasher()

    try:
        async with session_factory() as session:
            session.add(
                User(
                    email=email,
                    password_hash=hasher.hash(password),
                    first_name="Login",
                    last_name="API",
                    is_active=is_active,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.integration
async def test_login_endpoint_returns_tokens() -> None:
    email = "login-api@example.com"
    password = "very-secure-password"

    await _cleanup_user(email)
    await _create_user(
        email=email,
        password=password,
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": password,
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["access_token"]
        assert body["refresh_token"]
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 900

    finally:
        await _cleanup_user(email)


@pytest.mark.integration
async def test_login_endpoint_rejects_wrong_password() -> None:
    email = "login-wrong-password@example.com"

    await _cleanup_user(email)
    await _create_user(
        email=email,
        password="correct-password",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": "wrong-password",
                },
            )

        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid email or password"}
        assert response.headers["www-authenticate"] == "Bearer"

    finally:
        await _cleanup_user(email)


@pytest.mark.integration
async def test_login_endpoint_rejects_unknown_email() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "missing-user@example.com",
                "password": "any-password",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


@pytest.mark.integration
async def test_login_endpoint_rejects_inactive_user() -> None:
    email = "inactive-login@example.com"

    await _cleanup_user(email)
    await _create_user(
        email=email,
        password="correct-password",
        is_active=False,
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": "correct-password",
                },
            )

        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid email or password"}

    finally:
        await _cleanup_user(email)


@pytest.mark.integration
async def test_login_endpoint_hides_account_lockout_state() -> None:
    email = "locked-login@example.com"
    password = "correct-password"

    await _cleanup_user(email)
    await _create_user(
        email=email,
        password=password,
    )

    try:
        with TestClient(app) as client:
            for _ in range(5):
                failed_response = client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": email,
                        "password": "wrong-password",
                    },
                )

                assert failed_response.status_code == 401
                assert failed_response.json() == {"detail": "Invalid email or password"}

            locked_response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": password,
                },
            )

        assert locked_response.status_code == 401
        assert locked_response.json() == {"detail": "Invalid email or password"}
        assert locked_response.headers["www-authenticate"] == "Bearer"

    finally:
        await _cleanup_user(email)
