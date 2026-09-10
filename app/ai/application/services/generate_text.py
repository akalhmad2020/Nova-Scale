import logging
from time import perf_counter

from app.ai.application.ports.llm_provider import LLMProvider
from app.ai.application.runtime_exceptions import AIRequestLimitError, AIResponseLimitError
from app.ai.domain.models import LLMMessage, LLMRequest, LLMResponse

logger = logging.getLogger("novascale.ai")


class GenerateTextService:
    def __init__(
        self,
        provider: LLMProvider,
        *,
        max_prompt_characters: int = 32_000,
        max_system_prompt_characters: int = 16_000,
        max_response_characters: int = 32_000,
        max_output_tokens: int = 2_048,
        max_context_window: int = 8_192,
    ) -> None:
        self._provider = provider
        self._max_prompt_characters = max_prompt_characters
        self._max_system_prompt_characters = max_system_prompt_characters
        self._max_response_characters = max_response_characters
        self._max_output_tokens = max_output_tokens
        self._max_context_window = max_context_window

    async def execute(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        context_window: int = 2048,
    ) -> LLMResponse:
        self._validate_request_budget(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            context_window=context_window,
        )

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

        if len(response.content) > self._max_response_characters:
            logger.warning(
                "AI text generation response rejected",
                extra={
                    "ai_operation": "generate_text",
                    "ai_provider": provider_name,
                    "ai_model": response.model,
                    "ai_outcome": "response_limit_exceeded",
                    "response_character_count": len(response.content),
                },
            )
            raise AIResponseLimitError(
                "AI provider response exceeds the configured character limit"
            )

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

    def _validate_request_budget(
        self,
        *,
        prompt: str,
        system_prompt: str | None,
        max_tokens: int,
        context_window: int,
    ) -> None:
        if len(prompt) > self._max_prompt_characters:
            raise AIRequestLimitError("AI prompt exceeds the configured character limit")

        if system_prompt is not None and len(system_prompt) > self._max_system_prompt_characters:
            raise AIRequestLimitError("AI system prompt exceeds the configured character limit")

        if max_tokens < 1 or max_tokens > self._max_output_tokens:
            raise AIRequestLimitError("AI max_tokens exceeds the configured output-token budget")

        if context_window < 1 or context_window > self._max_context_window:
            raise AIRequestLimitError("AI context_window exceeds the configured context budget")
