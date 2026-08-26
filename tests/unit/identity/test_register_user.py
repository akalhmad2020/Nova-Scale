import pytest

from app.modules.identity.application.exceptions import (
    EmailAlreadyRegisteredError,
)
from app.modules.identity.application.use_cases.register_user import (
    RegisterUser,
    RegisterUserCommand,
)
from tests.unit.identity.fakes import (
    FakePasswordHasher,
    FakeUnitOfWork,
)


async def test_register_user_creates_user() -> None:
    uow = FakeUnitOfWork()
    hasher = FakePasswordHasher()

    use_case = RegisterUser(uow, hasher)

    command = RegisterUserCommand(
        email="Ahmed@Example.COM",
        password="secure-password",
        first_name="Ahmed",
        last_name="Akram",
    )

    user = await use_case.execute(command)

    assert user.email == "ahmed@example.com"
    assert user.password_hash == "hashed::secure-password"
    assert user.first_name == "Ahmed"
    assert user.last_name == "Akram"

    assert len(uow.users.users) == 1
    assert uow.users.users[0] is user


async def test_register_user_trims_names_and_email() -> None:
    uow = FakeUnitOfWork()
    hasher = FakePasswordHasher()

    use_case = RegisterUser(uow, hasher)

    user = await use_case.execute(
        RegisterUserCommand(
            email="  user@example.com  ",
            password="secure-password",
            first_name="  Ahmed  ",
            last_name="  Akram  ",
        )
    )

    assert user.email == "user@example.com"
    assert user.first_name == "Ahmed"
    assert user.last_name == "Akram"


async def test_register_user_rejects_duplicate_email() -> None:
    uow = FakeUnitOfWork()
    hasher = FakePasswordHasher()

    use_case = RegisterUser(uow, hasher)

    await use_case.execute(
        RegisterUserCommand(
            email="user@example.com",
            password="first-password",
            first_name="First",
            last_name="User",
        )
    )

    with pytest.raises(EmailAlreadyRegisteredError):
        await use_case.execute(
            RegisterUserCommand(
                email="USER@EXAMPLE.COM",
                password="second-password",
                first_name="Second",
                last_name="User",
            )
        )

    assert len(uow.users.users) == 1
    assert uow.rolled_back is True


async def test_register_user_does_not_store_plain_password() -> None:
    uow = FakeUnitOfWork()
    hasher = FakePasswordHasher()

    use_case = RegisterUser(uow, hasher)

    password = "super-secret-password"

    user = await use_case.execute(
        RegisterUserCommand(
            email="user@example.com",
            password=password,
            first_name="Ahmed",
            last_name="Akram",
        )
    )

    assert user.password_hash != password
    assert user.password_hash == f"hashed::{password}"


async def test_register_user_commits_transaction() -> None:
    uow = FakeUnitOfWork()
    hasher = FakePasswordHasher()

    use_case = RegisterUser(uow, hasher)

    await use_case.execute(
        RegisterUserCommand(
            email="user@example.com",
            password="secure-password",
            first_name="Ahmed",
            last_name="Akram",
        )
    )

    assert uow.flushed is True
    assert uow.committed is True
    assert uow.rolled_back is False
