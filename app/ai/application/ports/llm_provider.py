from typing import Protocol

from app.ai.domain.models import LLMRequest, LLMResponse


class LLMProvider(Protocol):
    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse: ...
