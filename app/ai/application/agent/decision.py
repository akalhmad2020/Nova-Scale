from dataclasses import dataclass
from typing import Literal

AgentRoute = Literal[
    "direct_answer",
    "get_shipment",
    "summarize_shipment",
    "analyze_shipment_operations",
    "retrieve_context",
]


@dataclass(frozen=True, slots=True)
class AgentDecision:
    route: AgentRoute
    shipment_identifier: str | None = None
