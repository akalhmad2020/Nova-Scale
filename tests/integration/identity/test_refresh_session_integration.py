from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.identity.application.exceptions import (
    InvalidRefreshTokenError,
)
from app.modules.identity.application.use_cases.refresh_session import (
    RefreshSession,
    RefreshSessionCommand,
)
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.access_token_service import (
    JWTAccessTokenService,
)
from app.modules.identity.infrastructure.security.refresh_token_service import (
    SecureRefreshTokenService,
)
from app.modules.identity.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


def make_access_token_service() -> JWTAccessTokenService:
    return JWTAccessTokenService(
        secret="integration-test-secret-that-is-long-enough-for-hs256",
        algorithm="HS256",
        ttl_minutes=15,
        issuer="novascale",
        audience="novascale-api",
    )


async def cleanup_user(
    session_factory: async_sessionmaker[AsyncSession],
    email: str,
) -> None:
    async with session_factory() as session:
        user_id = await session.scalar(select(User.id).where(User.email == email))

        if user_id is not None:
            await session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))

            await session.execute(delete(User).where(User.id == user_id))

        await session.commit()


@pytest.mark.integration
async def test_refresh_session_rotates_real_refresh_token(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    email = f"refresh-integration-{uuid4()}@example.com"

    refresh_token_service = SecureRefreshTokenService()
    old_refresh_token = refresh_token_service.generate()

    try:
        async with session_factory() as setup_session:
            user = User(
                email=email,
                password_hash="hashed-password",
                first_name="Refresh",
                last_name="Integration",
                is_active=True,
            )

            setup_session.add(user)
            await setup_session.flush()

            auth_session = AuthSession(
                user_id=user.id,
                refresh_token_hash=refresh_token_service.hash(old_refresh_token),
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )

            setup_session.add(auth_session)
            await setup_session.commit()

            user_id = user.id
            auth_session_id = auth_session.id

        use_case = RefreshSession(
            unit_of_work=SQLAlchemyUnitOfWork(session_factory),
            access_token_service=make_access_token_service(),
            refresh_token_service=refresh_token_service,
            refresh_token_ttl_days=30,
            access_token_ttl_minutes=15,
        )

        result = await use_case.execute(
            RefreshSessionCommand(
                refresh_token=old_refresh_token,
            )
        )

        assert result.access_token
        assert result.refresh_token
        assert result.refresh_token != old_refresh_token
        assert result.token_type == "bearer"
        assert result.expires_in == 900

        claims = make_access_token_service().decode(result.access_token)

        assert claims.subject == user_id

        new_refresh_token_hash = refresh_token_service.hash(result.refresh_token)

        async with session_factory() as verification_session:
            stored_session = await verification_session.scalar(
                select(AuthSession).where(AuthSession.id == auth_session_id)
            )

        assert stored_session is not None
        assert stored_session.refresh_token_hash == new_refresh_token_hash

    finally:
        await cleanup_user(session_factory, email)


@pytest.mark.integration
async def test_refresh_session_rejects_old_token_after_rotation(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    email = f"refresh-reuse-{uuid4()}@example.com"

    refresh_token_service = SecureRefreshTokenService()
    old_refresh_token = refresh_token_service.generate()

    try:
        async with session_factory() as setup_session:
            user = User(
                email=email,
                password_hash="hashed-password",
                first_name="Refresh",
                last_name="Reuse",
                is_active=True,
            )

            setup_session.add(user)
            await setup_session.flush()

            setup_session.add(
                AuthSession(
                    user_id=user.id,
                    refresh_token_hash=refresh_token_service.hash(old_refresh_token),
                    expires_at=datetime.now(UTC) + timedelta(days=30),
                )
            )

            await setup_session.commit()

        use_case = RefreshSession(
            unit_of_work=SQLAlchemyUnitOfWork(session_factory),
            access_token_service=make_access_token_service(),
            refresh_token_service=refresh_token_service,
            refresh_token_ttl_days=30,
            access_token_ttl_minutes=15,
        )

        first_result = await use_case.execute(
            RefreshSessionCommand(
                refresh_token=old_refresh_token,
            )
        )

        assert first_result.refresh_token != old_refresh_token

        with pytest.raises(InvalidRefreshTokenError):
            await use_case.execute(
                RefreshSessionCommand(
                    refresh_token=old_refresh_token,
                )
            )

    finally:
        await cleanup_user(session_factory, email)


@pytest.mark.integration
async def test_refresh_session_accepts_new_token_after_rotation(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    email = f"refresh-chain-{uuid4()}@example.com"

    refresh_token_service = SecureRefreshTokenService()
    original_refresh_token = refresh_token_service.generate()

    try:
        async with session_factory() as setup_session:
            user = User(
                email=email,
                password_hash="hashed-password",
                first_name="Refresh",
                last_name="Chain",
                is_active=True,
            )

            setup_session.add(user)
            await setup_session.flush()

            setup_session.add(
                AuthSession(
                    user_id=user.id,
                    refresh_token_hash=refresh_token_service.hash(original_refresh_token),
                    expires_at=datetime.now(UTC) + timedelta(days=30),
                )
            )

            await setup_session.commit()

        use_case = RefreshSession(
            unit_of_work=SQLAlchemyUnitOfWork(session_factory),
            access_token_service=make_access_token_service(),
            refresh_token_service=refresh_token_service,
            refresh_token_ttl_days=30,
            access_token_ttl_minutes=15,
        )

        first_result = await use_case.execute(
            RefreshSessionCommand(
                refresh_token=original_refresh_token,
            )
        )

        second_result = await use_case.execute(
            RefreshSessionCommand(
                refresh_token=first_result.refresh_token,
            )
        )

        assert second_result.access_token
        assert second_result.refresh_token
        assert second_result.refresh_token != first_result.refresh_token

    finally:
        await cleanup_user(session_factory, email)
