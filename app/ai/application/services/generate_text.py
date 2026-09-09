import logging
from time import perf_counter

from app.ai.application.ports.llm_provider import LLMProvider
from app.ai.domain.models import LLMMessage, LLMRequest, LLMResponse

logger = logging.getLogger("novascale.ai")


class GenerateTextService:
    def __init__(
        self,
        provider: LLMProvider,
    ) -> None:
        self._provider = provider

    async def execute(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        context_window: int = 2048,
    ) -> LLMResponse:
        messages: list[LLMMessage] = []

        if system_prompt is not None:
            messages.append(
                LLMMessage(
                    role="system",
                    content=system_prompt,
                )
            )

        messages.append(
            LLMMessage(
                role="user",
                content=prompt,
            )
        )

        request = LLMRequest(
            messages=tuple(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            context_window=context_window,
        )

        started_at = perf_counter()
        provider_name = type(self._provider).__name__

        try:
            response = await self._provider.generate(
                request,
            )
        except Exception:
            logger.exception(
                "AI text generation failed",
                extra={
                    "ai_operation": "generate_text",
                    "ai_provider": provider_name,
                    "ai_outcome": "failure",
                    "duration_ms": round(
                        (perf_counter() - started_at) * 1000,
                        2,
                    ),
                    "message_count": len(messages),
                    "max_tokens": max_tokens,
                    "context_window": context_window,
                    "prompt_character_count": len(prompt),
                },
            )
            raise

        logger.info(
            "AI text generation completed",
            extra={
                "ai_operation": "generate_text",
                "ai_provider": provider_name,
                "ai_model": response.model,
                "ai_outcome": "success",
                "duration_ms": round(
                    (perf_counter() - started_at) * 1000,
                    2,
                ),
                "provider_duration_ms": response.provider_duration_ms,
                "message_count": len(messages),
                "max_tokens": max_tokens,
                "context_window": context_window,
                "prompt_character_count": len(prompt),
                "response_character_count": len(response.content),
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
            },
        )

        return response
