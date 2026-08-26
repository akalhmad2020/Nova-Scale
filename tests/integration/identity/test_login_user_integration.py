import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.modules.identity.application.use_cases.login_user import (
    LoginUser,
    LoginUserCommand,
)
from app.modules.identity.infrastructure.models.auth_session import AuthSession
from app.modules.identity.infrastructure.models.user import User
from app.modules.identity.infrastructure.security.access_token_service import (
    JWTAccessTokenService,
)
from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)
from app.modules.identity.infrastructure.security.refresh_token_service import (
    SecureRefreshTokenService,
)
from app.modules.identity.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


@pytest.mark.integration
async def test_login_user_creates_real_tokens_and_auth_session() -> None:
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

    email = "login-integration@example.com"
    password = "very-secure-login-password"

    password_hasher = Argon2PasswordHasher()
    refresh_token_service = SecureRefreshTokenService()

    try:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(
                delete(AuthSession).where(
                    AuthSession.user_id.in_(select(User.id).where(User.email == email))
                )
            )
            await cleanup_session.execute(delete(User).where(User.email == email))
            await cleanup_session.commit()

        user = User(
            email=email,
            password_hash=password_hasher.hash(password),
            first_name="Login",
            last_name="Integration",
        )

        async with session_factory() as setup_session:
            setup_session.add(user)
            await setup_session.commit()
            await setup_session.refresh(user)

        access_token_service = JWTAccessTokenService(
            secret=settings.auth_jwt_secret,
            algorithm=settings.auth_jwt_algorithm,
            ttl_minutes=settings.access_token_ttl_minutes,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )

        use_case = LoginUser(
            unit_of_work=SQLAlchemyUnitOfWork(session_factory),
            password_hasher=password_hasher,
            access_token_service=access_token_service,
            refresh_token_service=refresh_token_service,
            refresh_token_ttl_days=settings.refresh_token_ttl_days,
            access_token_ttl_minutes=settings.access_token_ttl_minutes,
        )

        result = await use_case.execute(
            LoginUserCommand(
                email=email,
                password=password,
            )
        )

        assert result.access_token
        assert result.refresh_token
        assert result.token_type == "bearer"
        assert result.expires_in == settings.access_token_ttl_minutes * 60

        claims = access_token_service.decode(result.access_token)

        assert claims.subject == user.id
        assert claims.expires_at > claims.issued_at

        refresh_token_hash = refresh_token_service.hash(result.refresh_token)

        async with session_factory() as verification_session:
            session_result = await verification_session.execute(
                select(AuthSession).where(AuthSession.refresh_token_hash == refresh_token_hash)
            )

            stored_auth_session = session_result.scalar_one_or_none()

        assert stored_auth_session is not None
        assert stored_auth_session.user_id == user.id
        assert stored_auth_session.refresh_token_hash == refresh_token_hash
        assert stored_auth_session.refresh_token_hash != result.refresh_token
        assert stored_auth_session.revoked_at is None

    finally:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(
                delete(AuthSession).where(
                    AuthSession.user_id.in_(select(User.id).where(User.email == email))
                )
            )
            await cleanup_session.execute(delete(User).where(User.email == email))
            await cleanup_session.commit()

        await engine.dispose()
