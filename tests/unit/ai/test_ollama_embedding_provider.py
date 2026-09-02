import httpx
import pytest
from langchain_ollama import OllamaEmbeddings

from app.ai.infrastructure.embeddings.ollama_embedding_provider import (
    OllamaEmbeddingProvider,
)


@pytest.mark.asyncio
async def test_embed_text_succeeds_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    async def fake_embed_query(
        self: OllamaEmbeddings,
        text: str,
    ) -> list[float]:
        nonlocal attempts

        attempts += 1

        assert text == "shipment status"

        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(
        OllamaEmbeddings,
        "aembed_query",
        fake_embed_query,
    )

    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="nomic-embed-text",
        retry_delay_seconds=0.0,
    )

    result = await provider.embed_text("shipment status")

    assert result == (0.1, 0.2, 0.3)
    assert attempts == 1


@pytest.mark.asyncio
async def test_embed_text_retries_transient_failure_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    async def fake_embed_query(
        self: OllamaEmbeddings,
        text: str,
    ) -> list[float]:
        nonlocal attempts

        attempts += 1

        assert text == "shipment status"

        if attempts == 1:
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")

        return [0.4, 0.5, 0.6]

    monkeypatch.setattr(
        OllamaEmbeddings,
        "aembed_query",
        fake_embed_query,
    )

    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="nomic-embed-text",
        max_attempts=3,
        retry_delay_seconds=0.0,
    )

    result = await provider.embed_text("shipment status")

    assert result == (0.4, 0.5, 0.6)
    assert attempts == 2


@pytest.mark.asyncio
async def test_embed_text_reraises_after_max_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    async def fake_embed_query(
        self: OllamaEmbeddings,
        text: str,
    ) -> list[float]:
        nonlocal attempts

        attempts += 1

        assert text == "shipment status"

        raise httpx.ConnectError("Connection failed")

    monkeypatch.setattr(
        OllamaEmbeddings,
        "aembed_query",
        fake_embed_query,
    )

    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="nomic-embed-text",
        max_attempts=3,
        retry_delay_seconds=0.0,
    )

    with pytest.raises(httpx.ConnectError):
        await provider.embed_text("shipment status")

    assert attempts == 3


@pytest.mark.asyncio
async def test_embed_texts_retries_transient_failure_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    async def fake_embed_documents(
        self: OllamaEmbeddings,
        texts: list[str],
    ) -> list[list[float]]:
        nonlocal attempts

        attempts += 1

        assert texts == [
            "shipment one",
            "shipment two",
        ]

        if attempts == 1:
            raise httpx.ReadTimeout("Embedding request timed out")

        return [
            [0.1, 0.2],
            [0.3, 0.4],
        ]

    monkeypatch.setattr(
        OllamaEmbeddings,
        "aembed_documents",
        fake_embed_documents,
    )

    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="nomic-embed-text",
        max_attempts=3,
        retry_delay_seconds=0.0,
    )

    result = await provider.embed_texts(
        (
            "shipment one",
            "shipment two",
        )
    )

    assert result == (
        (0.1, 0.2),
        (0.3, 0.4),
    )
    assert attempts == 2
