from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.modules.identity.application.exceptions import (
    InvalidRefreshTokenError,
)
from app.modules.identity.application.ports.access_token_service import (
    AccessTokenClaims,
)
from app.modules.identity.application.use_cases.refresh_session import (
    RefreshSession,
    RefreshSessionCommand,
)
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.user import User
from tests.unit.identity.fakes import FakeUnitOfWork


class FakeAccessTokenService:
    def create(self, user_id: UUID) -> str:
        return f"access-token::{user_id}"

    def decode(self, token: str) -> AccessTokenClaims:
        return AccessTokenClaims(
            subject=uuid4(),
            token_id=uuid4(),
            issued_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )


class FakeRefreshTokenService:
    def generate(self) -> str:
        return "new-refresh-token"

    def hash(self, token: str) -> str:
        return f"hashed::{token}"


def make_user(
    *,
    email: str = "user@example.com",
    is_active: bool = True,
) -> User:
    return User(
        email=email,
        password_hash="hashed::password",
        first_name="Test",
        last_name="User",
        is_active=is_active,
    )


def make_auth_session(
    *,
    user_id: UUID,
    refresh_token_hash: str = "hashed::old-refresh-token",
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> AuthSession:
    return AuthSession(
        user_id=user_id,
        refresh_token_hash=refresh_token_hash,
        expires_at=expires_at or datetime.now(UTC) + timedelta(days=30),
        revoked_at=revoked_at,
    )


def make_use_case(
    uow: FakeUnitOfWork,
) -> RefreshSession:
    return RefreshSession(
        unit_of_work=uow,
        access_token_service=FakeAccessTokenService(),
        refresh_token_service=FakeRefreshTokenService(),
        refresh_token_ttl_days=30,
        access_token_ttl_minutes=15,
    )


async def test_refresh_session_rotates_refresh_token() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    user.id = uuid4()
    uow.users.add(user)

    auth_session = make_auth_session(
        user_id=user.id,
    )
    uow.auth_sessions.add(auth_session)

    use_case = make_use_case(uow)

    result = await use_case.execute(
        RefreshSessionCommand(
            refresh_token="old-refresh-token",
        )
    )

    assert result.access_token == f"access-token::{user.id}"
    assert result.refresh_token == "new-refresh-token"
    assert result.token_type == "bearer"
    assert result.expires_in == 900

    assert auth_session.refresh_token_hash == "hashed::new-refresh-token"


async def test_refresh_session_old_token_is_rejected_after_rotation() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    user.id = uuid4()
    uow.users.add(user)

    auth_session = make_auth_session(
        user_id=user.id,
    )
    uow.auth_sessions.add(auth_session)

    use_case = make_use_case(uow)

    await use_case.execute(
        RefreshSessionCommand(
            refresh_token="old-refresh-token",
        )
    )

    with pytest.raises(InvalidRefreshTokenError):
        await use_case.execute(
            RefreshSessionCommand(
                refresh_token="old-refresh-token",
            )
        )


async def test_refresh_session_rejects_unknown_token() -> None:
    uow = FakeUnitOfWork()
    use_case = make_use_case(uow)

    with pytest.raises(InvalidRefreshTokenError):
        await use_case.execute(
            RefreshSessionCommand(
                refresh_token="unknown-token",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_refresh_session_rejects_expired_session() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    user.id = uuid4()
    uow.users.add(user)

    auth_session = make_auth_session(
        user_id=user.id,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    uow.auth_sessions.add(auth_session)

    use_case = make_use_case(uow)

    with pytest.raises(InvalidRefreshTokenError):
        await use_case.execute(
            RefreshSessionCommand(
                refresh_token="old-refresh-token",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_refresh_session_rejects_revoked_session() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    user.id = uuid4()
    uow.users.add(user)

    auth_session = make_auth_session(
        user_id=user.id,
        revoked_at=datetime.now(UTC),
    )
    uow.auth_sessions.add(auth_session)

    use_case = make_use_case(uow)

    with pytest.raises(InvalidRefreshTokenError):
        await use_case.execute(
            RefreshSessionCommand(
                refresh_token="old-refresh-token",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_refresh_session_rejects_inactive_user() -> None:
    uow = FakeUnitOfWork()

    user = make_user(
        is_active=False,
    )
    user.id = uuid4()
    uow.users.add(user)

    auth_session = make_auth_session(
        user_id=user.id,
    )
    uow.auth_sessions.add(auth_session)

    use_case = make_use_case(uow)

    with pytest.raises(InvalidRefreshTokenError):
        await use_case.execute(
            RefreshSessionCommand(
                refresh_token="old-refresh-token",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_refresh_session_commits_successful_rotation() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    user.id = uuid4()
    uow.users.add(user)

    auth_session = make_auth_session(
        user_id=user.id,
    )
    uow.auth_sessions.add(auth_session)

    use_case = make_use_case(uow)

    await use_case.execute(
        RefreshSessionCommand(
            refresh_token="old-refresh-token",
        )
    )

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False
