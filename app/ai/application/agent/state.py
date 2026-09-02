from typing import TypedDict
from uuid import UUID

from app.ai.application.agent.decision import AgentRoute


class AgentState(TypedDict):
    tenant_id: UUID
    question: str
    route: AgentRoute | None
    shipment_id: UUID | None
    tool_result: str | None
    answer: str
