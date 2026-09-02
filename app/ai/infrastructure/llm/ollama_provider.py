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

        return LLMResponse(
            content=content,
            model=model,
        )
