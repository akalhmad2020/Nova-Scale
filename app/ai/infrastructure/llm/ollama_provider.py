from typing import Any

import httpx

from app.ai.application.ports.llm_provider import LLMProvider
from app.ai.domain.models import LLMRequest, LLMResponse


class OllamaLLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
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

        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
        ) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )

            response.raise_for_status()

        data: dict[str, Any] = response.json()

        message = data.get("message")

        if not isinstance(message, dict):
            raise RuntimeError("Ollama response is missing message")

        content = message.get("content")

        if not isinstance(content, str):
            raise RuntimeError("Ollama response is missing message content")

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
