import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
from langchain_ollama import OllamaEmbeddings

from app.ai.application.ports.embedding_provider import EmbeddingProvider

T = TypeVar("T")


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        max_attempts: int = 3,
        retry_delay_seconds: float = 0.5,
    ) -> None:
        self._embeddings = OllamaEmbeddings(
            base_url=base_url,
            model=model,
        )
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds

    async def embed_text(self, text: str) -> tuple[float, ...]:
        embedding = await self._with_retry(lambda: self._embeddings.aembed_query(text))

        return tuple(embedding)

    async def embed_texts(
        self,
        texts: tuple[str, ...],
    ) -> tuple[tuple[float, ...], ...]:
        embeddings = await self._with_retry(lambda: self._embeddings.aembed_documents(list(texts)))

        return tuple(tuple(embedding) for embedding in embeddings)

    async def _with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        for attempt in range(1, self._max_attempts + 1):
            try:
                return await operation()
            except (
                httpx.RemoteProtocolError,
                httpx.ConnectError,
                httpx.ReadTimeout,
            ):
                if attempt == self._max_attempts:
                    raise

                await asyncio.sleep(self._retry_delay_seconds * attempt)

        raise RuntimeError("Embedding retry loop exited unexpectedly")
