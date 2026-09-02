from typing import Protocol


class EmbeddingProvider(Protocol):
    async def embed_text(
        self,
        text: str,
    ) -> tuple[float, ...]: ...

    async def embed_texts(
        self,
        texts: tuple[str, ...],
    ) -> tuple[tuple[float, ...], ...]: ...
