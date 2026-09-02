from dataclasses import dataclass
from typing import Literal
from uuid import UUID

AgentRoute = Literal[
    "direct_answer",
    "get_shipment",
    "retrieve_context",
]


@dataclass(frozen=True, slots=True)
class AgentDecision:
    route: AgentRoute
    shipment_id: UUID | None = None
