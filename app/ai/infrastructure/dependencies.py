from app.ai.application.ports.embedding_provider import EmbeddingProvider
from app.ai.application.ports.llm_provider import LLMProvider
from app.ai.infrastructure.embeddings.ollama_embedding_provider import (
    OllamaEmbeddingProvider,
)
from app.ai.infrastructure.llm.ollama_provider import OllamaLLMProvider
from app.core.config import Settings


def build_llm_provider(
    settings: Settings,
) -> LLMProvider:
    if settings.ai_llm_provider == "ollama":
        return OllamaLLMProvider(
            base_url=settings.ai_ollama_base_url,
            model=settings.ai_ollama_model,
            timeout_seconds=settings.ai_ollama_timeout_seconds,
        )

    raise ValueError(f"Unsupported AI LLM provider: {settings.ai_llm_provider}")


def build_embedding_provider(
    settings: Settings,
) -> EmbeddingProvider:
    if settings.ai_embedding_provider == "ollama":
        return OllamaEmbeddingProvider(
            base_url=settings.ai_ollama_base_url,
            model=settings.ai_ollama_embedding_model,
        )

    raise ValueError(f"Unsupported AI embedding provider: {settings.ai_embedding_provider}")
