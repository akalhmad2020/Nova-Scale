from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    subject: UUID
    token_id: UUID
    issued_at: datetime
    expires_at: datetime


class AccessTokenService(Protocol):
    def create(self, user_id: UUID) -> str: ...

    def decode(self, token: str) -> AccessTokenClaims: ...
