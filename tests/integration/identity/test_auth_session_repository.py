from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.repositories.auth_session_repository import (
    AuthSessionRepository,
)


@pytest.mark.integration
async def test_auth_session_repository_adds_and_reads_session(
    db_session: AsyncSession,
) -> None:
    user = User(
        email="auth-session@example.com",
        password_hash="hashed-password",
        first_name="Auth",
        last_name="Session",
    )

    db_session.add(user)
    await db_session.flush()

    repository = AuthSessionRepository(db_session)

    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash="a" * 64,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    repository.add(auth_session)
    await db_session.flush()

    found_session = await repository.get_by_id(auth_session.id)

    assert found_session is not None
    assert found_session.id == auth_session.id
    assert found_session.user_id == user.id
    assert found_session.refresh_token_hash == "a" * 64
    assert found_session.revoked_at is None


@pytest.mark.integration
async def test_auth_session_repository_finds_session_by_refresh_token_hash(
    db_session: AsyncSession,
) -> None:
    user = User(
        email="refresh-lookup@example.com",
        password_hash="hashed-password",
        first_name="Refresh",
        last_name="Lookup",
    )

    db_session.add(user)
    await db_session.flush()

    repository = AuthSessionRepository(db_session)

    refresh_token_hash = "b" * 64

    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash=refresh_token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    repository.add(auth_session)
    await db_session.flush()

    found_session = await repository.get_by_refresh_token_hash(refresh_token_hash)

    assert found_session is not None
    assert found_session.id == auth_session.id
    assert found_session.refresh_token_hash == refresh_token_hash


@pytest.mark.integration
async def test_auth_session_repository_returns_none_for_unknown_hash(
    db_session: AsyncSession,
) -> None:
    repository = AuthSessionRepository(db_session)

    found_session = await repository.get_by_refresh_token_hash("c" * 64)

    assert found_session is None
