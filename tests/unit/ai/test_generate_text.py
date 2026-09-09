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
    assert request.max_tokens == 512
    assert request.context_window == 2048

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
        max_tokens=256,
        context_window=1024,
    )

    request = provider.requests[0]

    assert request.temperature == 0.1
    assert request.max_tokens == 256
    assert request.context_window == 1024

    assert len(request.messages) == 2

    assert request.messages[0].role == "system"
    assert request.messages[0].content == ("You are NovaScale's logistics assistant.")

    assert request.messages[1].role == "user"
    assert request.messages[1].content == "Summarize this shipment."


@pytest.mark.asyncio
async def test_generate_text_logs_ai_metadata_without_prompt_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = FakeLLMProvider()
    provider.response = provider.response.__class__(
        content="observed response",
        model="observed-model",
        prompt_tokens=42,
        completion_tokens=11,
        provider_duration_ms=123.4,
    )

    service = GenerateTextService(provider)

    with caplog.at_level(
        "INFO",
        logger="novascale.ai",
    ):
        await service.execute(
            prompt="sensitive shipment prompt",
            max_tokens=96,
            context_window=2048,
        )

    record = next(
        record
        for record in caplog.records
        if record.name == "novascale.ai" and record.getMessage() == "AI text generation completed"
    )

    metadata = vars(record)

    assert metadata["ai_operation"] == "generate_text"
    assert metadata["ai_provider"] == "FakeLLMProvider"
    assert metadata["ai_model"] == "observed-model"
    assert metadata["ai_outcome"] == "success"

    assert metadata["prompt_tokens"] == 42
    assert metadata["completion_tokens"] == 11
    assert metadata["provider_duration_ms"] == 123.4

    assert metadata["max_tokens"] == 96
    assert metadata["context_window"] == 2048
    assert metadata["prompt_character_count"] == len("sensitive shipment prompt")

    assert "sensitive shipment prompt" not in record.getMessage()
