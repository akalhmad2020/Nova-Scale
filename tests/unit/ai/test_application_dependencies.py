from app.ai.application.dependencies import build_generate_text_service
from app.ai.application.services.generate_text import GenerateTextService
from app.core.config import Settings


def test_build_generate_text_service() -> None:
    settings = Settings(
        auth_jwt_secret="test-secret",
        ai_llm_provider="ollama",
        ai_ollama_base_url="http://ollama:11434",
        ai_ollama_model="qwen2.5:3b",
        ai_ollama_timeout_seconds=180.0,
    )

    service = build_generate_text_service(settings)

    assert isinstance(service, GenerateTextService)
