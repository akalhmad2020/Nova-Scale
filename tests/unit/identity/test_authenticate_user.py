from datetime import UTC, datetime

import pytest

from app.modules.identity.application.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
)
from app.modules.identity.application.use_cases.authenticate_user import (
    AuthenticateUser,
    AuthenticateUserCommand,
)
from app.modules.identity.infrastructure.models.user import User
from tests.unit.identity.fakes import (
    FakePasswordHasher,
    FakeUnitOfWork,
)


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
    )


async def test_authenticate_user_returns_user_for_valid_credentials() -> None:
    uow = FakeUnitOfWork()
    hasher = FakePasswordHasher()

    user = make_user()
    uow.users.add(user)

    use_case = AuthenticateUser(uow, hasher)

    authenticated_user = await use_case.execute(
        AuthenticateUserCommand(
            email="USER@EXAMPLE.COM",
            password="correct-password",
        )
    )

    assert authenticated_user is user


async def test_authenticate_user_rejects_unknown_email() -> None:
    uow = FakeUnitOfWork()
    hasher = FakePasswordHasher()

    use_case = AuthenticateUser(uow, hasher)

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            AuthenticateUserCommand(
                email="missing@example.com",
                password="correct-password",
            )
        )


async def test_authenticate_user_rejects_wrong_password() -> None:
    uow = FakeUnitOfWork()
    hasher = FakePasswordHasher()

    uow.users.add(make_user())

    use_case = AuthenticateUser(uow, hasher)

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            AuthenticateUserCommand(
                email="user@example.com",
                password="wrong-password",
            )
        )


async def test_authenticate_user_rejects_inactive_user() -> None:
    uow = FakeUnitOfWork()
    hasher = FakePasswordHasher()

    uow.users.add(
        make_user(
            is_active=False,
        )
    )

    use_case = AuthenticateUser(uow, hasher)

    with pytest.raises(InactiveUserError):
        await use_case.execute(
            AuthenticateUserCommand(
                email="user@example.com",
                password="correct-password",
            )
        )


async def test_authenticate_user_rejects_soft_deleted_user() -> None:
    uow = FakeUnitOfWork()
    hasher = FakePasswordHasher()

    user = make_user()
    user.deleted_at = datetime.now(UTC)

    uow.users.add(user)

    use_case = AuthenticateUser(uow, hasher)

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            AuthenticateUserCommand(
                email="user@example.com",
                password="correct-password",
            )
        )
