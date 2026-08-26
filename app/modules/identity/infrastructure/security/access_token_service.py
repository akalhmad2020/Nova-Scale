from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from app.modules.identity.application.ports.access_token_service import (
    AccessTokenClaims,
)


class InvalidAccessTokenError(Exception):
    """Raised when an access token is invalid."""


class ExpiredAccessTokenError(InvalidAccessTokenError):
    """Raised when an access token has expired."""


class JWTAccessTokenService:
    def __init__(
        self,
        *,
        secret: str,
        algorithm: str,
        ttl_minutes: int,
        issuer: str,
        audience: str,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._ttl_minutes = ttl_minutes
        self._issuer = issuer
        self._audience = audience

    def create(self, user_id: UUID) -> str:
        issued_at = datetime.now(UTC)
        expires_at = issued_at + timedelta(minutes=self._ttl_minutes)
        token_id = uuid4()

        payload = {
            "sub": str(user_id),
            "jti": str(token_id),
            "type": "access",
            "iat": issued_at,
            "exp": expires_at,
            "iss": self._issuer,
            "aud": self._audience,
        }

        return jwt.encode(
            payload,
            self._secret,
            algorithm=self._algorithm,
        )

    def decode(self, token: str) -> AccessTokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                audience=self._audience,
                options={
                    "require": [
                        "sub",
                        "jti",
                        "type",
                        "iat",
                        "exp",
                        "iss",
                        "aud",
                    ]
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredAccessTokenError from exc
        except jwt.PyJWTError as exc:
            raise InvalidAccessTokenError from exc

        if payload.get("type") != "access":
            raise InvalidAccessTokenError

        try:
            subject = UUID(payload["sub"])
            token_id = UUID(payload["jti"])
            issued_at = datetime.fromtimestamp(payload["iat"], tz=UTC)
            expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidAccessTokenError from exc

        return AccessTokenClaims(
            subject=subject,
            token_id=token_id,
            issued_at=issued_at,
            expires_at=expires_at,
        )
