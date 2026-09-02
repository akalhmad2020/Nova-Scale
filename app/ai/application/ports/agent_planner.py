from typing import Protocol

from app.ai.application.agent.decision import AgentDecision


class AgentPlanner(Protocol):
    async def plan(
        self,
        *,
        question: str,
    ) -> AgentDecision: ...
