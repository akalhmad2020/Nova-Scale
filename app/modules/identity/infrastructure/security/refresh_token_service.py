import hashlib
import secrets


class SecureRefreshTokenService:
    def generate(self) -> str:
        return secrets.token_urlsafe(48)

    def hash(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
