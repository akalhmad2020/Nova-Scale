from dataclasses import dataclass
from typing import Literal

from app.modules.shipments.domain.enums import ShipmentStatus

AgentRoute = Literal[
    "direct_answer",
    "get_shipment",
    "get_shipments",
    "summarize_shipment",
    "analyze_shipment_operations",
    "retrieve_context",
    "transition_shipment_status",
    "update_shipment_notes",
]


@dataclass(frozen=True, slots=True)
class AgentDecision:
    route: AgentRoute
    shipment_identifier: str | None = None
    shipment_identifiers: tuple[str, ...] = ()
    target_shipment_status: ShipmentStatus | None = None
    shipment_notes: str | None = None
