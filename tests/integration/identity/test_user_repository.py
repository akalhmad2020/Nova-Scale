import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.repositories.user_repository import (
    UserRepository,
)


@pytest.mark.integration
async def test_user_repository_adds_and_reads_user(
    db_session: AsyncSession,
) -> None:
    repository = UserRepository(db_session)

    user = User(
        email="repository-test@example.com",
        password_hash="hashed-password",
        first_name="Repository",
        last_name="Test",
    )

    repository.add(user)
    await db_session.flush()

    assert user.id is not None

    stored_user = await repository.get_by_id(user.id)

    assert stored_user is not None
    assert stored_user.email == "repository-test@example.com"
    assert stored_user.first_name == "Repository"


@pytest.mark.integration
async def test_user_repository_email_lookup_is_case_insensitive(
    db_session: AsyncSession,
) -> None:
    repository = UserRepository(db_session)

    user = User(
        email="CaseSensitive@Example.COM",
        password_hash="hashed-password",
        first_name="Case",
        last_name="Test",
    )

    repository.add(user)
    await db_session.flush()

    stored_user = await repository.get_by_email(
        "casesensitive@example.com",
    )

    assert stored_user is not None
    assert stored_user.id == user.id


@pytest.mark.integration
async def test_database_rejects_case_insensitive_duplicate_email(
    db_session: AsyncSession,
) -> None:
    first_user = User(
        email="duplicate@example.com",
        password_hash="hash-one",
        first_name="First",
        last_name="User",
    )

    second_user = User(
        email="DUPLICATE@EXAMPLE.COM",
        password_hash="hash-two",
        first_name="Second",
        last_name="User",
    )

    db_session.add(first_user)
    await db_session.flush()

    db_session.add(second_user)

    with pytest.raises(IntegrityError):
        await db_session.flush()
