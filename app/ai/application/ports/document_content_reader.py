from typing import Protocol


class DocumentContentReader(Protocol):
    async def read_text(
        self,
        *,
        storage_key: str,
        content_type: str,
    ) -> str: ...
