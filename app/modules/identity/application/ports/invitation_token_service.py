from typing import Protocol


class InvitationTokenService(Protocol):
    def generate_token(self) -> str: ...

    def hash_token(
        self,
        token: str,
    ) -> str: ...
