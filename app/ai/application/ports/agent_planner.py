from typing import Protocol

from app.ai.application.agent.conversation_context import (
    ConversationContext,
)
from app.ai.application.agent.decision import AgentDecision


class AgentPlanner(Protocol):
    async def plan(
        self,
        *,
        question: str,
        conversation_context: ConversationContext | None = None,
    ) -> AgentDecision: ...
