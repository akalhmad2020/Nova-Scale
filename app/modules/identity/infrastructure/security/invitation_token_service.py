import hashlib
import secrets


class SecureInvitationTokenService:
    def generate_token(self) -> str:
        return secrets.token_urlsafe(32)

    def hash_token(
        self,
        token: str,
    ) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
