import pytest

from app.ai.domain.models import LLMMessage, LLMRequest
from app.ai.infrastructure.llm.ollama_provider import OllamaLLMProvider
from app.core.config import get_settings


@pytest.mark.integration
@pytest.mark.external_ai
@pytest.mark.asyncio
async def test_ollama_provider_generates_response() -> None:
    settings = get_settings()

    provider = OllamaLLMProvider(
        base_url=settings.ai_ollama_base_url,
        model=settings.ai_ollama_model,
        timeout_seconds=settings.ai_ollama_timeout_seconds,
    )

    response = await provider.generate(
        LLMRequest(
            messages=(
                LLMMessage(
                    role="user",
                    content="Reply with exactly: NovaScale AI OK",
                ),
            ),
            temperature=0.0,
        )
    )

    assert response.content.strip()
    assert response.model == settings.ai_ollama_model
