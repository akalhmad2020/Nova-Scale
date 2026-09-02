import pytest

from app.ai.infrastructure.embeddings.ollama_embedding_provider import (
    OllamaEmbeddingProvider,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ollama_embedding_provider_generates_embedding() -> None:
    provider = OllamaEmbeddingProvider(
        base_url="http://host.docker.internal:11434",
        model="nomic-embed-text",
    )

    embedding = await provider.embed_text(
        "NovaScale shipment tracking",
    )

    assert embedding
    assert len(embedding) > 0
    assert all(isinstance(value, float) for value in embedding)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ollama_embedding_provider_generates_multiple_embeddings() -> None:
    provider = OllamaEmbeddingProvider(
        base_url="http://host.docker.internal:11434",
        model="nomic-embed-text",
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
