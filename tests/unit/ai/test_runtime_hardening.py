import pytest

from app.ai.application.runtime_exceptions import AIRequestLimitError, AIResponseLimitError
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.domain.models import LLMResponse
from tests.unit.ai.fakes import FakeLLMProvider


@pytest.mark.asyncio
async def test_generate_text_rejects_oversized_prompt_before_provider_call() -> None:
    provider = FakeLLMProvider()
    service = GenerateTextService(provider, max_prompt_characters=10)

    with pytest.raises(AIRequestLimitError):
        await service.execute(prompt="x" * 11)

    assert provider.requests == []


@pytest.mark.asyncio
async def test_generate_text_rejects_excessive_output_token_budget() -> None:
    provider = FakeLLMProvider()
    service = GenerateTextService(provider, max_output_tokens=128)

    with pytest.raises(AIRequestLimitError):
        await service.execute(prompt="hello", max_tokens=129)

    assert provider.requests == []


@pytest.mark.asyncio
async def test_generate_text_rejects_oversized_provider_response() -> None:
    provider = FakeLLMProvider()
    provider.response = LLMResponse(content="x" * 11, model="fake-model")
    service = GenerateTextService(provider, max_response_characters=10)

    with pytest.raises(AIResponseLimitError):
        await service.execute(prompt="hello")
