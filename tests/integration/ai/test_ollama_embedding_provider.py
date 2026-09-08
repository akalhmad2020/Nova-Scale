import pytest

from app.ai.infrastructure.embeddings.ollama_embedding_provider import (
    OllamaEmbeddingProvider,
)
from app.core.config import get_settings


@pytest.mark.integration
@pytest.mark.external_ai
@pytest.mark.asyncio
async def test_ollama_embedding_provider_generates_embedding() -> None:
    settings = get_settings()

    provider = OllamaEmbeddingProvider(
        base_url=settings.ai_ollama_base_url,
        model=settings.ai_ollama_embedding_model,
    )

    embedding = await provider.embed_text(
        "NovaScale shipment tracking",
    )

    assert embedding
    assert len(embedding) > 0
    assert all(isinstance(value, float) for value in embedding)


@pytest.mark.integration
@pytest.mark.external_ai
@pytest.mark.asyncio
async def test_ollama_embedding_provider_generates_multiple_embeddings() -> None:
    settings = get_settings()

    provider = OllamaEmbeddingProvider(
        base_url=settings.ai_ollama_base_url,
        model=settings.ai_ollama_embedding_model,
    )

    embeddings = await provider.embed_texts(
        (
            "NovaScale shipment tracking",
            "NovaScale invoice payment",
        )
    )

    assert len(embeddings) == 2
    assert all(embedding for embedding in embeddings)
    assert len(embeddings[0]) == len(embeddings[1])
