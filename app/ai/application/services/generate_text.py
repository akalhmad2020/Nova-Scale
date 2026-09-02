from app.ai.application.ports.llm_provider import LLMProvider
from app.ai.domain.models import LLMMessage, LLMRequest, LLMResponse


class GenerateTextService:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def execute(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
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
        )

        return await self._provider.generate(request)
