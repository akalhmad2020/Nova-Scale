import httpx
import pytest

from app.ai.application.runtime_exceptions import AIProviderUnavailableError
from app.ai.domain.models import LLMMessage, LLMRequest
from app.ai.infrastructure.llm.ollama_provider import OllamaLLMProvider


def make_request() -> LLMRequest:
    return LLMRequest(
        messages=(
            LLMMessage(
                role="user",
                content="Reply with hello",
            ),
        ),
        temperature=0.0,
        max_tokens=32,
        context_window=512,
    )


@pytest.mark.asyncio
async def test_ollama_provider_translates_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_post(
        self: httpx.AsyncClient,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        del self
        del url
        del kwargs

        raise httpx.ConnectError(
            "connection refused",
        )

    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        failing_post,
    )

    provider = OllamaLLMProvider(
        base_url="http://ollama.invalid",
        model="qwen2.5:3b",
        timeout_seconds=1.0,
        max_attempts=1,
        retry_backoff_seconds=0.0,
    )

    with pytest.raises(
        AIProviderUnavailableError,
        match="Ollama is temporarily unavailable",
    ):
        await provider.generate(make_request())


@pytest.mark.asyncio
async def test_ollama_provider_translates_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_post(
        self: httpx.AsyncClient,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        del self
        del url
        del kwargs

        raise httpx.ReadTimeout(
            "provider timed out",
        )

    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        failing_post,
    )

    provider = OllamaLLMProvider(
        base_url="http://ollama.invalid",
        model="qwen2.5:3b",
        timeout_seconds=1.0,
        max_attempts=1,
        retry_backoff_seconds=0.0,
    )

    with pytest.raises(
        AIProviderUnavailableError,
        match="Ollama is temporarily unavailable",
    ):
        await provider.generate(make_request())


@pytest.mark.asyncio
async def test_ollama_provider_translates_retryable_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_post(
        self: httpx.AsyncClient,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        del self
        del kwargs

        request = httpx.Request(
            "POST",
            url,
        )

        return httpx.Response(
            status_code=503,
            request=request,
        )

    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        failing_post,
    )

    provider = OllamaLLMProvider(
        base_url="http://ollama.invalid",
        model="qwen2.5:3b",
        timeout_seconds=1.0,
        max_attempts=1,
        retry_backoff_seconds=0.0,
    )

    with pytest.raises(
        AIProviderUnavailableError,
        match="Ollama is temporarily unavailable",
    ):
        await provider.generate(make_request())


@pytest.mark.asyncio
async def test_ollama_provider_translates_non_retryable_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_post(
        self: httpx.AsyncClient,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        del self
        del kwargs

        request = httpx.Request(
            "POST",
            url,
        )

        return httpx.Response(
            status_code=400,
            request=request,
        )

    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        failing_post,
    )

    provider = OllamaLLMProvider(
        base_url="http://ollama.invalid",
        model="qwen2.5:3b",
        timeout_seconds=1.0,
        max_attempts=1,
        retry_backoff_seconds=0.0,
    )

    with pytest.raises(
        AIProviderUnavailableError,
        match="Ollama rejected the request",
    ):
        await provider.generate(make_request())


@pytest.mark.asyncio
async def test_ollama_provider_rejects_invalid_json_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def invalid_json_post(
        self: httpx.AsyncClient,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        del self
        del kwargs

        request = httpx.Request(
            "POST",
            url,
        )

        return httpx.Response(
            status_code=200,
            content=b"not-json",
            request=request,
        )

    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        invalid_json_post,
    )

    provider = OllamaLLMProvider(
        base_url="http://ollama.invalid",
        model="qwen2.5:3b",
        timeout_seconds=1.0,
        max_attempts=1,
        retry_backoff_seconds=0.0,
    )

    with pytest.raises(
        AIProviderUnavailableError,
        match="invalid JSON response",
    ):
        await provider.generate(make_request())
