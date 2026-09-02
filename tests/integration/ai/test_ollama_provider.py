import pytest

from app.ai.domain.models import LLMMessage, LLMRequest
from app.ai.infrastructure.llm.ollama_provider import OllamaLLMProvider


@pytest.mark.integration
@pytest.mark.external_ai
@pytest.mark.asyncio
async def test_ollama_provider_generates_response() -> None:
    provider = OllamaLLMProvider(
        base_url="http://host.docker.internal:11434",
        model="qwen2.5:3b",
        timeout_seconds=180.0,
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
    assert response.model == "qwen2.5:3b"
