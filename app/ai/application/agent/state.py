from typing import TypedDict
from uuid import UUID

from app.ai.application.agent.action_models import AgentActionProposal
from app.ai.application.agent.conversation_context import ConversationContext
from app.ai.application.agent.decision import AgentRoute
from app.ai.application.agent.shipment_resolution_models import (
    MultiShipmentResolutionItem,
)
from app.modules.shipments.domain.enums import ShipmentStatus


class AgentState(TypedDict):
    tenant_id: UUID
    role_id: UUID
    question: str
    conversation_context: ConversationContext | None

    route: AgentRoute | None

    shipment_identifier: str | None
    shipment_id: UUID | None

    shipment_identifiers: tuple[str, ...]
    shipment_ids: tuple[UUID, ...]
    shipment_resolutions: tuple[
        MultiShipmentResolutionItem,
        ...,
    ]

    target_shipment_status: ShipmentStatus | None
    shipment_notes: str | None
    action_proposal: AgentActionProposal | None

    continuation_route: AgentRoute | None
    continuation_original_identifier: str | None

    tool_result: str | None

    authorization_denied: bool
    shipment_resolution_ambiguous: bool
    shipment_resolution_not_found: bool

    answer: str
