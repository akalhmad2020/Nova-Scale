from typing import Never
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.ai.application.action_exceptions import (
    AgentActionConflictError,
    AgentActionExecutionError,
    AgentActionInProgressError,
    AgentActionNotFoundError,
    AgentActionPermissionDeniedError,
    PendingAgentActionExistsError,
)
from app.ai.application.agent.action_models import (
    AgentActionMutationResult,
    AgentActionProposal,
    StoredAgentAction,
)
from app.ai.application.agent.authorization import PermissionChecker
from app.ai.application.ports.agent_action_repository import AgentActionRepository
from app.modules.audit.application.contracts import AuditRecord
from app.modules.audit.application.use_cases.record_audit_log import (
    RecordAuditLogUseCase,
)
from app.modules.audit.domain.enums import AuditActorType, AuditOutcome
from app.modules.identity.domain.permissions import Permissions
from app.modules.shipments.application.exceptions import ShipmentError
from app.modules.shipments.application.use_cases.get_shipment import (
    GetShipment,
    GetShipmentQuery,
)
from app.modules.shipments.application.use_cases.transition_shipment_status import (
    TransitionShipmentStatus,
    TransitionShipmentStatusCommand,
)
from app.modules.shipments.application.use_cases.update_shipment import (
    UpdateShipment,
    UpdateShipmentCommand,
)
from app.modules.shipments.domain.enums import ShipmentStatus


class AgentActionService:
    def __init__(
        self,
        *,
        repository: AgentActionRepository,
        get_shipment: GetShipment,
        transition_shipment_status: TransitionShipmentStatus,
        update_shipment: UpdateShipment,
        record_audit_log: RecordAuditLogUseCase,
        permission_checker: PermissionChecker,
    ) -> None:
        self._repository = repository
        self._get_shipment = get_shipment
        self._transition_shipment_status = transition_shipment_status
        self._update_shipment = update_shipment
        self._record_audit_log = record_audit_log
        self._permission_checker = permission_checker

    async def get_active_for_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> StoredAgentAction | None:
        return await self._repository.get_active_for_conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

    async def propose(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        proposal: AgentActionProposal,
    ) -> StoredAgentAction:
        existing = await self.get_active_for_conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if existing is not None:
            raise PendingAgentActionExistsError

        try:
            action = await self._repository.create_action(
                tenant_id=tenant_id,
                user_id=user_id,
                conversation_id=conversation_id,
                idempotency_key=uuid4(),
                proposal=proposal,
            )

            await self._record_audit(
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                action_name="ai.action.proposed",
                outcome=AuditOutcome.SUCCESS,
            )

            await self._repository.flush()
        except IntegrityError as exc:
            await self._repository.rollback()
            raise PendingAgentActionExistsError from exc

        return action

    async def confirm(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
        role_id: UUID,
    ) -> AgentActionMutationResult:
        current = await self._require_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action_id=action_id,
        )

        await self._require_confirmation_permissions(
            role_id=role_id,
            action=current,
        )

        if current.status == "executed":
            return AgentActionMutationResult(
                action=current,
                changed=False,
            )

        if current.status == "executing":
            raise AgentActionInProgressError

        if current.status != "pending_confirmation":
            raise AgentActionConflictError(
                f"Action cannot be confirmed from status '{current.status}'."
            )

        claimed = await self._repository.claim_for_execution(
            tenant_id=tenant_id,
            user_id=user_id,
            action_id=action_id,
        )

        if claimed is None:
            raise AgentActionInProgressError

        await self._record_audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action=claimed,
            action_name="ai.action.confirmed",
            outcome=AuditOutcome.SUCCESS,
        )

        # Keep the execution claim uncommitted while the domain action runs.
        # The row lock serializes concurrent confirmations, while the shipment
        # use case remains the only writer of shipment state. The action row is
        # committed only after the execution outcome is known.
        try:
            result_summary = await self._execute_claimed_action(
                tenant_id=tenant_id,
                user_id=user_id,
                action=claimed,
            )
        except AgentActionExecutionError as exc:
            await self._fail_action(
                tenant_id=tenant_id,
                user_id=user_id,
                action=claimed,
                reason=str(exc),
            )
        except ShipmentError as exc:
            await self._fail_action(
                tenant_id=tenant_id,
                user_id=user_id,
                action=claimed,
                reason="The shipment action could not be completed safely.",
                cause=exc,
            )

        executed = await self._repository.mark_executed(
            tenant_id=tenant_id,
            user_id=user_id,
            action_id=claimed.id,
            result_summary=result_summary,
        )

        await self._record_audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action=executed,
            action_name="ai.action.executed",
            outcome=AuditOutcome.SUCCESS,
        )
        await self._repository.commit()

        return AgentActionMutationResult(
            action=executed,
            changed=True,
        )

    async def cancel(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
    ) -> AgentActionMutationResult:
        cancelled = await self._repository.mark_cancelled(
            tenant_id=tenant_id,
            user_id=user_id,
            action_id=action_id,
        )

        if cancelled is None:
            current = await self._require_action(
                tenant_id=tenant_id,
                user_id=user_id,
                action_id=action_id,
            )

            if current.status == "cancelled":
                return AgentActionMutationResult(
                    action=current,
                    changed=False,
                )

            if current.status == "executing":
                raise AgentActionInProgressError

            raise AgentActionConflictError(
                f"Action cannot be cancelled from status '{current.status}'."
            )

        await self._record_audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action=cancelled,
            action_name="ai.action.cancelled",
            outcome=AuditOutcome.SUCCESS,
        )
        await self._repository.commit()

        return AgentActionMutationResult(
            action=cancelled,
            changed=True,
        )

    async def rollback(self) -> None:
        await self._repository.rollback()

    async def _execute_claimed_action(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action: StoredAgentAction,
    ) -> str:
        shipment = await self._get_shipment.execute(
            GetShipmentQuery(
                tenant_id=tenant_id,
                shipment_id=action.resource_id,
            )
        )

        current_status = ShipmentStatus(shipment.status)

        if action.action_type == "transition_shipment_status":
            if current_status.value != action.expected_status:
                raise AgentActionExecutionError(
                    "Shipment status changed after the action was proposed. "
                    "Create a new action using the current shipment state."
                )

            if action.target_status is None:
                raise AgentActionExecutionError(
                    "The stored action is missing its target shipment status."
                )

            target_status = ShipmentStatus(action.target_status)

            updated = await self._transition_shipment_status.execute(
                TransitionShipmentStatusCommand(
                    tenant_id=tenant_id,
                    actor_id=user_id,
                    shipment_id=shipment.id,
                    target_status=target_status,
                )
            )

            return (
                f"Shipment {updated.tracking_number} status changed "
                f"from {current_status.value} to {target_status.value}."
            )

        if action.action_type == "update_shipment_notes":
            if shipment.notes != action.expected_notes:
                raise AgentActionExecutionError(
                    "Shipment notes changed after the action was proposed. "
                    "Create a new action before replacing the current notes."
                )

            if action.new_notes is None:
                raise AgentActionExecutionError(
                    "The stored action is missing the new shipment notes."
                )

            updated = await self._update_shipment.execute(
                UpdateShipmentCommand(
                    tenant_id=tenant_id,
                    actor_id=user_id,
                    shipment_id=shipment.id,
                    customer_id=shipment.customer_id,
                    origin_location_id=shipment.origin_location_id,
                    destination_location_id=shipment.destination_location_id,
                    tracking_number=shipment.tracking_number,
                    reference=shipment.reference,
                    service_type=shipment.service_type,
                    description=shipment.description,
                    weight=shipment.weight,
                    weight_unit=shipment.weight_unit,
                    notes=action.new_notes,
                )
            )

            return f"Shipment {updated.tracking_number} notes were updated."

        raise AgentActionExecutionError(
            f"Unsupported stored AI action type '{action.action_type}'."
        )

    async def _fail_action(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action: StoredAgentAction,
        reason: str,
        cause: Exception | None = None,
    ) -> Never:
        failed = await self._repository.mark_failed(
            tenant_id=tenant_id,
            user_id=user_id,
            action_id=action.id,
            failure_reason=reason,
        )

        await self._record_audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action=failed,
            action_name="ai.action.failed",
            outcome=AuditOutcome.FAILURE,
        )
        await self._repository.commit()

        if cause is not None:
            raise AgentActionExecutionError(reason) from cause

        raise AgentActionExecutionError(reason)

    async def _require_action(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
    ) -> StoredAgentAction:
        action = await self._repository.get_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action_id=action_id,
        )

        if action is None:
            raise AgentActionNotFoundError

        return action

    async def _require_confirmation_permissions(
        self,
        *,
        role_id: UUID,
        action: StoredAgentAction,
    ) -> None:
        if action.action_type == "transition_shipment_status":
            required_permissions = (
                Permissions.SHIPMENT_READ,
                Permissions.SHIPMENT_TRANSITION,
            )
        elif action.action_type == "update_shipment_notes":
            required_permissions = (
                Permissions.SHIPMENT_READ,
                Permissions.SHIPMENT_UPDATE,
            )
        else:
            raise AgentActionConflictError(f"Unsupported AI action type '{action.action_type}'.")

        for permission_code in required_permissions:
            allowed = await self._permission_checker(
                role_id,
                permission_code,
            )

            if not allowed:
                raise AgentActionPermissionDeniedError

    async def _record_audit(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action: StoredAgentAction,
        action_name: str,
        outcome: AuditOutcome,
    ) -> None:
        await self._record_audit_log.execute(
            AuditRecord(
                tenant_id=tenant_id,
                actor_type=AuditActorType.USER,
                actor_id=user_id,
                action=action_name,
                resource_type="ai_agent_action",
                resource_id=action.id,
                outcome=outcome,
                metadata={
                    "source": "ai_agent",
                    "action_type": action.action_type,
                    "action_status": action.status,
                    "shipment_id": str(action.resource_id),
                    "idempotency_key": str(action.idempotency_key),
                },
            )
        )
