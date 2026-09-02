from app.ai.infrastructure.dependencies import build_llm_provider
from app.ai.infrastructure.llm.ollama_provider import OllamaLLMProvider
from app.core.config import Settings


def test_build_llm_provider_builds_ollama_provider() -> None:
    settings = Settings(
        auth_jwt_secret="test-secret",
        ai_llm_provider="ollama",
        ai_ollama_base_url="http://ollama:11434",
        ai_ollama_model="qwen2.5:3b",
        ai_ollama_timeout_seconds=180.0,
    )

    provider = build_llm_provider(settings)

    assert isinstance(provider, OllamaLLMProvider)
