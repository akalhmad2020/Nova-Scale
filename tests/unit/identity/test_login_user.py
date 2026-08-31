from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.modules.identity.application.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
)
from app.modules.identity.application.ports.access_token_service import (
    AccessTokenClaims,
)
from app.modules.identity.application.use_cases.login_user import (
    LoginUser,
    LoginUserCommand,
)
from app.modules.identity.infrastructure.models.user import User
from tests.unit.identity.fakes import (
    FakePasswordHasher,
    FakeUnitOfWork,
)


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
        return "raw-refresh-token"

    def hash(self, token: str) -> str:
        return f"hashed::{token}"


class RehashRequiredPasswordHasher:
    def hash(self, password: str) -> str:
        return f"new-hash::{password}"

    def verify(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        return password == "correct-password" and password_hash == "old-hash::correct-password"

    def needs_rehash(self, password_hash: str) -> bool:
        return password_hash.startswith("old-hash::")


def make_user(
    *,
    email: str = "user@example.com",
    password_hash: str = "hashed::correct-password",
    is_active: bool = True,
) -> User:
    return User(
        email=email,
        password_hash=password_hash,
        first_name="Test",
        last_name="User",
        is_active=is_active,
        failed_login_attempts=0,
        locked_until=None,
    )


def make_use_case(
    uow: FakeUnitOfWork,
) -> LoginUser:
    return LoginUser(
        unit_of_work=uow,
        password_hasher=FakePasswordHasher(),
        access_token_service=FakeAccessTokenService(),
        refresh_token_service=FakeRefreshTokenService(),
        refresh_token_ttl_days=30,
        access_token_ttl_minutes=15,
        max_failed_attempts=5,
        lockout_minutes=15,
    )


async def test_login_returns_access_and_refresh_tokens() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    uow.users.add(user)

    use_case = make_use_case(uow)

    result = await use_case.execute(
        LoginUserCommand(
            email="user@example.com",
            password="correct-password",
        )
    )

    assert result.access_token == f"access-token::{user.id}"
    assert result.refresh_token == "raw-refresh-token"
    assert result.token_type == "bearer"
    assert result.expires_in == 900


async def test_login_normalizes_email() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    uow.users.add(user)

    use_case = make_use_case(uow)

    result = await use_case.execute(
        LoginUserCommand(
            email="  USER@EXAMPLE.COM  ",
            password="correct-password",
        )
    )

    assert result.access_token == f"access-token::{user.id}"


async def test_login_rehashes_password_when_hash_needs_upgrade() -> None:
    uow = FakeUnitOfWork()

    user = make_user(
        password_hash="old-hash::correct-password",
    )
    uow.users.add(user)

    use_case = LoginUser(
        unit_of_work=uow,
        password_hasher=RehashRequiredPasswordHasher(),
        access_token_service=FakeAccessTokenService(),
        refresh_token_service=FakeRefreshTokenService(),
        refresh_token_ttl_days=30,
        access_token_ttl_minutes=15,
        max_failed_attempts=5,
        lockout_minutes=15,
    )

    await use_case.execute(
        LoginUserCommand(
            email="user@example.com",
            password="correct-password",
        )
    )

    assert user.password_hash == "new-hash::correct-password"
    assert uow.committed is True


async def test_login_creates_auth_session() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    uow.users.add(user)

    use_case = make_use_case(uow)

    await use_case.execute(
        LoginUserCommand(
            email="user@example.com",
            password="correct-password",
        )
    )

    assert len(uow.auth_sessions.sessions) == 1

    auth_session = uow.auth_sessions.sessions[0]

    assert auth_session.user_id == user.id
    assert auth_session.refresh_token_hash == "hashed::raw-refresh-token"
    assert auth_session.revoked_at is None


async def test_login_does_not_store_raw_refresh_token() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    uow.users.add(user)

    use_case = make_use_case(uow)

    result = await use_case.execute(
        LoginUserCommand(
            email="user@example.com",
            password="correct-password",
        )
    )

    auth_session = uow.auth_sessions.sessions[0]

    assert auth_session.refresh_token_hash != result.refresh_token
    assert result.refresh_token == "raw-refresh-token"


async def test_login_flushes_and_commits_transaction() -> None:
    uow = FakeUnitOfWork()

    uow.users.add(make_user())

    use_case = make_use_case(uow)

    await use_case.execute(
        LoginUserCommand(
            email="user@example.com",
            password="correct-password",
        )
    )

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False


async def test_login_rejects_unknown_email() -> None:
    uow = FakeUnitOfWork()

    use_case = make_use_case(uow)

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            LoginUserCommand(
                email="missing@example.com",
                password="correct-password",
            )
        )

    assert uow.auth_sessions.sessions == []
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_login_rejects_wrong_password() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    uow.users.add(user)

    use_case = make_use_case(uow)

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            LoginUserCommand(
                email="user@example.com",
                password="wrong-password",
            )
        )

    assert uow.auth_sessions.sessions == []
    assert user.failed_login_attempts == 1
    assert user.locked_until is None
    assert uow.committed is True
    assert uow.rolled_back is True


async def test_login_rejects_inactive_user() -> None:
    uow = FakeUnitOfWork()

    uow.users.add(
        make_user(
            is_active=False,
        )
    )

    use_case = make_use_case(uow)

    with pytest.raises(InactiveUserError):
        await use_case.execute(
            LoginUserCommand(
                email="user@example.com",
                password="correct-password",
            )
        )

    assert uow.auth_sessions.sessions == []
    assert uow.committed is False
    assert uow.rolled_back is True


async def test_login_locks_user_after_max_failed_attempts() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    uow.users.add(user)

    use_case = make_use_case(uow)

    for _ in range(4):
        with pytest.raises(InvalidCredentialsError):
            await use_case.execute(
                LoginUserCommand(
                    email="user@example.com",
                    password="wrong-password",
                )
            )

        assert user.locked_until is None

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            LoginUserCommand(
                email="user@example.com",
                password="wrong-password",
            )
        )

    assert user.failed_login_attempts == 5
    assert user.locked_until is not None


async def test_login_rejects_locked_user_even_with_correct_password() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    user.failed_login_attempts = 5
    user.locked_until = datetime.now(UTC) + timedelta(minutes=10)

    uow.users.add(user)

    use_case = make_use_case(uow)

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            LoginUserCommand(
                email="user@example.com",
                password="correct-password",
            )
        )

    assert uow.auth_sessions.sessions == []


async def test_login_allows_attempt_after_lock_expires() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    user.failed_login_attempts = 5
    user.locked_until = datetime.now(UTC) - timedelta(minutes=1)

    uow.users.add(user)

    use_case = make_use_case(uow)

    result = await use_case.execute(
        LoginUserCommand(
            email="user@example.com",
            password="correct-password",
        )
    )

    assert result.access_token == f"access-token::{user.id}"
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


async def test_successful_login_resets_failed_login_attempts() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    user.failed_login_attempts = 3

    uow.users.add(user)

    use_case = make_use_case(uow)

    await use_case.execute(
        LoginUserCommand(
            email="user@example.com",
            password="correct-password",
        )
    )

    assert user.failed_login_attempts == 0
    assert user.locked_until is None


async def test_failed_attempt_after_expired_lock_starts_new_attempt_window() -> None:
    uow = FakeUnitOfWork()

    user = make_user()
    user.failed_login_attempts = 5
    user.locked_until = datetime.now(UTC) - timedelta(minutes=1)

    uow.users.add(user)

    use_case = make_use_case(uow)

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            LoginUserCommand(
                email="user@example.com",
                password="wrong-password",
            )
        )

    assert user.failed_login_attempts == 1
    assert user.locked_until is None
