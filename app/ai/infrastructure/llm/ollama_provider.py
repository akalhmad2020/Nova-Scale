import asyncio
from typing import Any

import httpx

from app.ai.application.ports.llm_provider import LLMProvider
from app.ai.application.runtime_exceptions import AIProviderUnavailableError
from app.ai.domain.models import LLMRequest, LLMResponse

_RETRYABLE_STATUS_CODES = frozenset({429, 502, 503, 504})


class OllamaLLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 120.0,
        max_attempts: int = 2,
        retry_backoff_seconds: float = 0.25,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        if retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must not be negative")

        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._retry_backoff_seconds = retry_backoff_seconds

    async def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in request.messages
            ],
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
                "num_ctx": request.context_window,
            },
        }

        response = await self._post_with_retry(payload)

        try:
            data: dict[str, Any] = response.json()
        except ValueError as exc:
            raise AIProviderUnavailableError("Ollama returned an invalid JSON response") from exc

        message = data.get("message")
        if not isinstance(message, dict):
            raise AIProviderUnavailableError("Ollama response is missing message")

        content = message.get("content")
        if not isinstance(content, str):
            raise AIProviderUnavailableError("Ollama response is missing message content")

        model = data.get("model")
        if not isinstance(model, str):
            model = self._model

        prompt_tokens = data.get("prompt_eval_count")
        completion_tokens = data.get("eval_count")
        total_duration = data.get("total_duration")

        return LLMResponse(
            content=content,
            model=model,
            prompt_tokens=(prompt_tokens if isinstance(prompt_tokens, int) else None),
            completion_tokens=(completion_tokens if isinstance(completion_tokens, int) else None),
            provider_duration_ms=(
                total_duration / 1_000_000 if isinstance(total_duration, int | float) else None
            ),
        )

    async def _post_with_retry(
        self,
        payload: dict[str, Any],
    ) -> httpx.Response:
        last_error: Exception | None = None

        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
        ) as client:
            for attempt in range(1, self._max_attempts + 1):
                try:
                    response = await client.post(
                        f"{self._base_url}/api/chat",
                        json=payload,
                    )
                    response.raise_for_status()
                    return response

                except (
                    httpx.TimeoutException,
                    httpx.ConnectError,
                ) as exc:
                    last_error = exc

                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code not in _RETRYABLE_STATUS_CODES:
                        raise AIProviderUnavailableError("Ollama rejected the request") from exc

                    last_error = exc

                if attempt < self._max_attempts:
                    await asyncio.sleep(self._retry_backoff_seconds * attempt)

        if last_error is None:
            raise AIProviderUnavailableError("Ollama request failed without an error")

        raise AIProviderUnavailableError("Ollama is temporarily unavailable") from last_error
