from dataclasses import dataclass
from typing import Literal

from app.ai.application.agent.decision import AgentRoute

AgentContinuationKind = Literal["shipment_selection",]

ShipmentContinuationRoute = Literal[
    "get_shipment",
    "summarize_shipment",
    "analyze_shipment_operations",
]


@dataclass(frozen=True, slots=True)
class AgentContinuation:
    kind: AgentContinuationKind
    route: ShipmentContinuationRoute
    original_identifier: str


@dataclass(frozen=True, slots=True)
class AgentExecutionResult:
    answer: str
    continuation: AgentContinuation | None = None


def is_shipment_continuation_route(
    route: AgentRoute,
) -> bool:
    return route in {
        "get_shipment",
        "summarize_shipment",
        "analyze_shipment_operations",
    }
