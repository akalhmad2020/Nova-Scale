from typing import Protocol


class RefreshTokenService(Protocol):
    def generate(self) -> str: ...

    def hash(self, token: str) -> str: ...
