import pytest

from app.ai.application.services.generate_text import GenerateTextService
from tests.unit.ai.fakes import FakeLLMProvider


@pytest.mark.asyncio
async def test_generate_text_builds_user_message_and_returns_provider_response() -> None:
    provider = FakeLLMProvider()
    service = GenerateTextService(provider)

    response = await service.execute(
        prompt="Where is shipment SHP-100?",
    )

    assert response.content == "fake response"
    assert response.model == "fake-model"

    assert len(provider.requests) == 1

    request = provider.requests[0]

    assert request.temperature == 0.2
    assert len(request.messages) == 1
    assert request.messages[0].role == "user"
    assert request.messages[0].content == "Where is shipment SHP-100?"


@pytest.mark.asyncio
async def test_generate_text_includes_system_prompt_when_provided() -> None:
    provider = FakeLLMProvider()
    service = GenerateTextService(provider)

    await service.execute(
        prompt="Summarize this shipment.",
        system_prompt="You are NovaScale's logistics assistant.",
        temperature=0.1,
    )

    request = provider.requests[0]

    assert request.temperature == 0.1
    assert len(request.messages) == 2

    assert request.messages[0].role == "system"
    assert request.messages[0].content == "You are NovaScale's logistics assistant."

    assert request.messages[1].role == "user"
    assert request.messages[1].content == "Summarize this shipment."
