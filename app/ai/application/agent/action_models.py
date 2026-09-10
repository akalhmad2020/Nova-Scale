from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.shipments.domain.enums import ShipmentStatus

AgentActionType = Literal[
    "transition_shipment_status",
    "update_shipment_notes",
]

AgentActionStatus = Literal[
    "pending_confirmation",
    "executing",
    "executed",
    "cancelled",
    "failed",
]


@dataclass(frozen=True, slots=True)
class AgentActionProposal:
    action_type: AgentActionType
    shipment_id: UUID
    shipment_identifier: str
    expected_status: ShipmentStatus
    summary: str
    target_status: ShipmentStatus | None = None
    expected_notes: str | None = None
    new_notes: str | None = None

    @property
    def confirmation_message(self) -> str:
        return (
            f"{self.summary}\n\n"
            "This action changes NovaScale data and requires explicit "
            "confirmation before execution."
        )


@dataclass(frozen=True, slots=True)
class StoredAgentAction:
    id: UUID
    tenant_id: UUID
    user_id: UUID
    conversation_id: UUID
    idempotency_key: UUID
    action_type: AgentActionType
    status: AgentActionStatus
    resource_type: str
    resource_id: UUID
    shipment_identifier: str
    expected_status: str
    summary: str
    created_at: datetime
    updated_at: datetime
    target_status: str | None = None
    expected_notes: str | None = None
    new_notes: str | None = None
    result_summary: str | None = None
    failure_reason: str | None = None
    confirmed_at: datetime | None = None
    executed_at: datetime | None = None
    cancelled_at: datetime | None = None
    failed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AgentActionMutationResult:
    action: StoredAgentAction
    changed: bool
