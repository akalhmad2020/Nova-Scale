from typing import TypedDict
from uuid import UUID

from app.ai.application.agent.conversation_context import (
    ConversationContext,
)
from app.ai.application.agent.decision import AgentRoute
from app.ai.application.agent.shipment_resolution_models import (
    MultiShipmentResolutionItem,
)


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

    continuation_route: AgentRoute | None
    continuation_original_identifier: str | None

    tool_result: str | None

    authorization_denied: bool
    shipment_resolution_ambiguous: bool

    answer: str
