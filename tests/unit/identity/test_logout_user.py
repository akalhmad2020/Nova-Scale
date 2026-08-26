from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.identity.application.exceptions import (
    InvalidRefreshTokenError,
)
from app.modules.identity.application.use_cases.logout_user import (
    LogoutUser,
    LogoutUserCommand,
)
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from tests.unit.identity.fakes import FakeUnitOfWork


class FakeRefreshTokenService:
    def generate(self) -> str:
        return "generated-refresh-token"

    def hash(self, token: str) -> str:
        return f"hashed::{token}"


def make_auth_session() -> AuthSession:
    return AuthSession(
        user_id=uuid4(),
        refresh_token_hash="hashed::refresh-token",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )


def make_use_case(
    uow: FakeUnitOfWork,
) -> LogoutUser:
    return LogoutUser(
        unit_of_work=uow,
        refresh_token_service=FakeRefreshTokenService(),
    )


async def test_logout_revokes_auth_session() -> None:
    uow = FakeUnitOfWork()

    auth_session = make_auth_session()
    uow.auth_sessions.add(auth_session)

    use_case = make_use_case(uow)

    await use_case.execute(
        LogoutUserCommand(
            refresh_token="refresh-token",
        )
    )

    assert auth_session.revoked_at is not None


async def test_logout_flushes_and_commits() -> None:
    uow = FakeUnitOfWork()

    uow.auth_sessions.add(make_auth_session())

    use_case = make_use_case(uow)

    await use_case.execute(
        LogoutUserCommand(
            refresh_token="refresh-token",
        )
    )

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False


async def test_logout_rejects_unknown_refresh_token() -> None:
    uow = FakeUnitOfWork()

    use_case = make_use_case(uow)

    with pytest.raises(InvalidRefreshTokenError):
        await use_case.execute(
            LogoutUserCommand(
                refresh_token="unknown-refresh-token",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True


async def test_logout_rejects_already_revoked_session() -> None:
    uow = FakeUnitOfWork()

    auth_session = make_auth_session()
    auth_session.revoked_at = datetime.now(UTC)

    uow.auth_sessions.add(auth_session)

    use_case = make_use_case(uow)

    with pytest.raises(InvalidRefreshTokenError):
        await use_case.execute(
            LogoutUserCommand(
                refresh_token="refresh-token",
            )
        )

    assert uow.committed is False
    assert uow.rolled_back is True
