from uuid import UUID

from app.ai.application.action_exceptions import AgentActionProposalRejectedError
from app.ai.application.agent.action_models import AgentActionProposal
from app.modules.shipments.application.use_cases.get_shipment import (
    GetShipment,
    GetShipmentQuery,
)
from app.modules.shipments.domain.enums import ShipmentStatus
from app.modules.shipments.domain.lifecycle import can_transition_shipment_status

MAX_AI_NOTES_LENGTH = 2000


class PrepareShipmentActionService:
    def __init__(
        self,
        *,
        get_shipment: GetShipment,
    ) -> None:
        self._get_shipment = get_shipment

    async def prepare_transition(
        self,
        *,
        tenant_id: UUID,
        shipment_id: UUID,
        shipment_identifier: str,
        target_status: ShipmentStatus,
    ) -> AgentActionProposal:
        shipment = await self._get_shipment.execute(
            GetShipmentQuery(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
            )
        )

        current_status = ShipmentStatus(shipment.status)

        if current_status == target_status:
            raise AgentActionProposalRejectedError(
                f"Shipment is already in status '{target_status.value}'."
            )

        if not can_transition_shipment_status(
            current_status,
            target_status,
        ):
            raise AgentActionProposalRejectedError(
                "The requested shipment status transition is not allowed "
                f"from '{current_status.value}' to '{target_status.value}'."
            )

        return AgentActionProposal(
            action_type="transition_shipment_status",
            shipment_id=shipment.id,
            shipment_identifier=shipment_identifier,
            expected_status=current_status,
            target_status=target_status,
            summary=(
                f"Transition shipment {shipment.tracking_number} "
                f"from {current_status.value} to {target_status.value}."
            ),
        )

    async def prepare_notes_update(
        self,
        *,
        tenant_id: UUID,
        shipment_id: UUID,
        shipment_identifier: str,
        new_notes: str,
    ) -> AgentActionProposal:
        normalized_notes = " ".join(new_notes.split())

        if not normalized_notes:
            raise AgentActionProposalRejectedError("Shipment notes must not be empty.")

        if len(normalized_notes) > MAX_AI_NOTES_LENGTH:
            raise AgentActionProposalRejectedError(
                f"Shipment notes must not exceed {MAX_AI_NOTES_LENGTH} characters."
            )

        shipment = await self._get_shipment.execute(
            GetShipmentQuery(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
            )
        )

        current_notes = shipment.notes

        if current_notes == normalized_notes:
            raise AgentActionProposalRejectedError("The shipment already has those notes.")

        display_notes = normalized_notes
        if len(display_notes) > 180:
            display_notes = display_notes[:177].rstrip() + "..."

        return AgentActionProposal(
            action_type="update_shipment_notes",
            shipment_id=shipment.id,
            shipment_identifier=shipment_identifier,
            expected_status=ShipmentStatus(shipment.status),
            expected_notes=current_notes,
            new_notes=normalized_notes,
            summary=(f'Update notes for shipment {shipment.tracking_number} to "{display_notes}".'),
        )
