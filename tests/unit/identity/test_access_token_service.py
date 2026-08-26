from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.modules.identity.infrastructure.security.access_token_service import (
    ExpiredAccessTokenError,
    InvalidAccessTokenError,
    JWTAccessTokenService,
)

TEST_SECRET = "test-secret-key-for-hs256-unit-tests-123456"
DIFFERENT_TEST_SECRET = "another-test-secret-key-for-hs256-12345678"


def make_service() -> JWTAccessTokenService:
    return JWTAccessTokenService(
        secret=TEST_SECRET,
        algorithm="HS256",
        ttl_minutes=15,
        issuer="novascale",
        audience="novascale-api",
    )


def test_create_and_decode_access_token() -> None:
    service = make_service()
    user_id = uuid4()

    token = service.create(user_id)
    claims = service.decode(token)

    assert claims.subject == user_id
    assert claims.token_id is not None
    assert claims.expires_at > claims.issued_at


def test_access_token_has_expected_lifetime() -> None:
    service = make_service()
    user_id = uuid4()

    token = service.create(user_id)
    claims = service.decode(token)

    lifetime = claims.expires_at - claims.issued_at

    assert lifetime == timedelta(minutes=15)


def test_decode_rejects_token_signed_with_different_secret() -> None:
    service = make_service()

    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "jti": str(uuid4()),
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
            "iss": "novascale",
            "aud": "novascale-api",
        },
        DIFFERENT_TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        service.decode(token)


def test_decode_rejects_wrong_issuer() -> None:
    service = make_service()

    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "jti": str(uuid4()),
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
            "iss": "another-service",
            "aud": "novascale-api",
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        service.decode(token)


def test_decode_rejects_wrong_audience() -> None:
    service = make_service()

    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "jti": str(uuid4()),
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
            "iss": "novascale",
            "aud": "another-api",
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        service.decode(token)


def test_decode_rejects_non_access_token() -> None:
    service = make_service()

    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "jti": str(uuid4()),
            "type": "refresh",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
            "iss": "novascale",
            "aud": "novascale-api",
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        service.decode(token)


def test_decode_rejects_expired_token() -> None:
    service = make_service()

    now = datetime.now(UTC)

    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "jti": str(uuid4()),
            "type": "access",
            "iat": now - timedelta(minutes=20),
            "exp": now - timedelta(minutes=5),
            "iss": "novascale",
            "aud": "novascale-api",
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(ExpiredAccessTokenError):
        service.decode(token)
