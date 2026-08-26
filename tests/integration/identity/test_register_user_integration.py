import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.modules.identity.application.exceptions import (
    EmailAlreadyRegisteredError,
)
from app.modules.identity.application.use_cases.register_user import (
    RegisterUser,
    RegisterUserCommand,
)
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)
from app.modules.identity.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


@pytest.mark.integration
async def test_register_user_persists_user() -> None:
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

    email = "register-integration@example.com"

    try:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(delete(User).where(User.email == email))
            await cleanup_session.commit()

        use_case = RegisterUser(
            SQLAlchemyUnitOfWork(session_factory),
            Argon2PasswordHasher(),
        )

        user = await use_case.execute(
            RegisterUserCommand(
                email=email,
                password="integration-secure-password",
                first_name="Integration",
                last_name="User",
            )
        )

        assert user.id is not None
        assert user.email == email
        assert user.password_hash != "integration-secure-password"

        async with session_factory() as verification_session:
            result = await verification_session.execute(select(User).where(User.email == email))
            stored_user = result.scalar_one_or_none()

        assert stored_user is not None
        assert stored_user.id == user.id
        assert stored_user.email == email

    finally:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(delete(User).where(User.email == email))
            await cleanup_session.commit()

        await engine.dispose()


@pytest.mark.integration
async def test_register_user_rejects_duplicate_email() -> None:
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

    email = "duplicate-register@example.com"

    try:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(delete(User).where(User.email == email))
            await cleanup_session.commit()

        use_case = RegisterUser(
            SQLAlchemyUnitOfWork(session_factory),
            Argon2PasswordHasher(),
        )

        await use_case.execute(
            RegisterUserCommand(
                email=email,
                password="first-password",
                first_name="First",
                last_name="User",
            )
        )

        with pytest.raises(EmailAlreadyRegisteredError):
            await use_case.execute(
                RegisterUserCommand(
                    email="DUPLICATE-REGISTER@EXAMPLE.COM",
                    password="second-password",
                    first_name="Second",
                    last_name="User",
                )
            )

        async with session_factory() as verification_session:
            result = await verification_session.execute(select(User).where(User.email == email))
            users = result.scalars().all()

        assert len(users) == 1

    finally:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(delete(User).where(User.email == email))
            await cleanup_session.commit()

        await engine.dispose()
