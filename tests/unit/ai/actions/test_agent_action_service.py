from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.ai.application.action_exceptions import (
    AgentActionExecutionError,
    AgentActionPermissionDeniedError,
)
from app.ai.application.agent.action_models import (
    AgentActionProposal,
    AgentActionStatus,
    AgentActionType,
    StoredAgentAction,
)
from app.ai.application.ports.agent_action_repository import AgentActionRepository
from app.ai.application.services.agent_action_service import AgentActionService
from app.modules.audit.application.use_cases.record_audit_log import (
    RecordAuditLogUseCase,
)
from app.modules.shipments.application.use_cases.get_shipment import GetShipment
from app.modules.shipments.application.use_cases.transition_shipment_status import (
    TransitionShipmentStatus,
)
from app.modules.shipments.application.use_cases.update_shipment import UpdateShipment
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment

TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
ROLE_ID = UUID("33333333-3333-3333-3333-333333333333")
CONVERSATION_ID = UUID("44444444-4444-4444-4444-444444444444")
ACTION_ID = UUID("55555555-5555-5555-5555-555555555555")
SHIPMENT_ID = UUID("66666666-6666-6666-6666-666666666666")


def make_action(
    *,
    status: AgentActionStatus,
    action_type: AgentActionType = "transition_shipment_status",
    expected_status: str,
    target_status: str | None = None,
    expected_notes: str | None = None,
    new_notes: str | None = None,
    result_summary: str | None = None,
    failure_reason: str | None = None,
) -> StoredAgentAction:
    now = datetime.now(UTC)

    return StoredAgentAction(
        id=ACTION_ID,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        conversation_id=CONVERSATION_ID,
        idempotency_key=uuid4(),
        action_type=action_type,
        status=status,
        resource_type="shipment",
        resource_id=SHIPMENT_ID,
        shipment_identifier="SHIP-001",
        expected_status=expected_status,
        target_status=target_status,
        expected_notes=expected_notes,
        new_notes=new_notes,
        summary="Confirm shipment action",
        result_summary=result_summary,
        failure_reason=failure_reason,
        created_at=now,
        updated_at=now,
    )


def make_shipment(
    *,
    status: ShipmentStatus,
    notes: str | None = "Original notes",
) -> Shipment:
    return cast(
        Shipment,
        SimpleNamespace(
            id=SHIPMENT_ID,
            tenant_id=TENANT_ID,
            customer_id=uuid4(),
            origin_location_id=uuid4(),
            destination_location_id=uuid4(),
            tracking_number="SHIP-001",
            reference="ORDER-100",
            status=status,
            service_type=next(iter(ServiceType)),
            description="Test shipment",
            weight=Decimal("10"),
            weight_unit=next(iter(WeightUnit)),
            notes=notes,
        ),
    )


def make_service(
    *,
    repository_mock: MagicMock,
    get_shipment_mock: MagicMock,
    transition_mock: MagicMock,
    update_mock: MagicMock,
    audit_mock: MagicMock,
    permission_allowed: bool = True,
) -> AgentActionService:
    async def permission_checker(
        role_id: UUID,
        permission_code: str,
    ) -> bool:
        assert role_id == ROLE_ID
        assert permission_code
        return permission_allowed

    return AgentActionService(
        repository=cast(AgentActionRepository, repository_mock),
        get_shipment=cast(GetShipment, get_shipment_mock),
        transition_shipment_status=cast(
            TransitionShipmentStatus,
            transition_mock,
        ),
        update_shipment=cast(UpdateShipment, update_mock),
        record_audit_log=cast(RecordAuditLogUseCase, audit_mock),
        permission_checker=permission_checker,
    )


def make_mocks() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
    repository = MagicMock(spec=AgentActionRepository)
    repository.get_active_for_conversation = AsyncMock(return_value=None)
    repository.create_action = AsyncMock()
    repository.get_action = AsyncMock()
    repository.claim_for_execution = AsyncMock()
    repository.mark_executed = AsyncMock()
    repository.mark_cancelled = AsyncMock()
    repository.mark_failed = AsyncMock()
    repository.flush = AsyncMock()
    repository.commit = AsyncMock()
    repository.rollback = AsyncMock()

    get_shipment = MagicMock(spec=GetShipment)
    get_shipment.execute = AsyncMock()

    transition = MagicMock(spec=TransitionShipmentStatus)
    transition.execute = AsyncMock()

    update = MagicMock(spec=UpdateShipment)
    update.execute = AsyncMock()

    audit = MagicMock(spec=RecordAuditLogUseCase)
    audit.execute = AsyncMock()

    return repository, get_shipment, transition, update, audit


@pytest.mark.asyncio
async def test_propose_persists_action_without_committing_turn() -> None:
    repository, get_shipment, transition, update, audit = make_mocks()
    status = next(iter(ShipmentStatus))
    proposal = AgentActionProposal(
        action_type="update_shipment_notes",
        shipment_id=SHIPMENT_ID,
        shipment_identifier="SHIP-001",
        expected_status=status,
        expected_notes="Old",
        new_notes="New",
        summary="Update notes",
    )
    stored = make_action(
        status="pending_confirmation",
        action_type="update_shipment_notes",
        expected_status=status.value,
        expected_notes="Old",
        new_notes="New",
    )
    repository.create_action.return_value = stored

    service = make_service(
        repository_mock=repository,
        get_shipment_mock=get_shipment,
        transition_mock=transition,
        update_mock=update,
        audit_mock=audit,
    )

    result = await service.propose(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        conversation_id=CONVERSATION_ID,
        proposal=proposal,
    )

    assert result == stored
    repository.flush.assert_awaited_once()
    repository.commit.assert_not_awaited()
    audit.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_transition_is_idempotent_after_execution() -> None:
    repository, get_shipment, transition, update, audit = make_mocks()
    statuses = list(ShipmentStatus)
    current = statuses[0]
    target = next(status for status in statuses if status != current)

    pending = make_action(
        status="pending_confirmation",
        expected_status=current.value,
        target_status=target.value,
    )
    executing = make_action(
        status="executing",
        expected_status=current.value,
        target_status=target.value,
    )
    executed = make_action(
        status="executed",
        expected_status=current.value,
        target_status=target.value,
        result_summary="Shipment SHIP-001 status changed.",
    )

    repository.get_action.side_effect = [pending, executed]
    repository.claim_for_execution.return_value = executing
    repository.mark_executed.return_value = executed

    shipment = make_shipment(status=current)
    updated = make_shipment(status=target)
    get_shipment.execute.return_value = shipment
    transition.execute.return_value = updated

    service = make_service(
        repository_mock=repository,
        get_shipment_mock=get_shipment,
        transition_mock=transition,
        update_mock=update,
        audit_mock=audit,
    )

    first = await service.confirm(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        role_id=ROLE_ID,
        action_id=ACTION_ID,
    )
    second = await service.confirm(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        role_id=ROLE_ID,
        action_id=ACTION_ID,
    )

    assert first.changed is True
    assert first.action.status == "executed"
    assert second.changed is False
    transition.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_rechecks_current_permission() -> None:
    repository, get_shipment, transition, update, audit = make_mocks()
    status = next(iter(ShipmentStatus))
    repository.get_action.return_value = make_action(
        status="pending_confirmation",
        expected_status=status.value,
        target_status=status.value,
    )

    service = make_service(
        repository_mock=repository,
        get_shipment_mock=get_shipment,
        transition_mock=transition,
        update_mock=update,
        audit_mock=audit,
        permission_allowed=False,
    )

    with pytest.raises(AgentActionPermissionDeniedError):
        await service.confirm(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            role_id=ROLE_ID,
            action_id=ACTION_ID,
        )

    repository.claim_for_execution.assert_not_awaited()
    transition.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_notes_action_rejects_stale_notes() -> None:
    repository, get_shipment, transition, update, audit = make_mocks()
    status = next(iter(ShipmentStatus))
    pending = make_action(
        status="pending_confirmation",
        action_type="update_shipment_notes",
        expected_status=status.value,
        expected_notes="Original notes",
        new_notes="Keep upright",
    )
    executing = make_action(
        status="executing",
        action_type="update_shipment_notes",
        expected_status=status.value,
        expected_notes="Original notes",
        new_notes="Keep upright",
    )
    failed = make_action(
        status="failed",
        action_type="update_shipment_notes",
        expected_status=status.value,
        expected_notes="Original notes",
        new_notes="Keep upright",
        failure_reason="Shipment notes changed",
    )

    repository.get_action.return_value = pending
    repository.claim_for_execution.return_value = executing
    repository.mark_failed.return_value = failed
    get_shipment.execute.return_value = make_shipment(
        status=status,
        notes="Changed by another user",
    )

    service = make_service(
        repository_mock=repository,
        get_shipment_mock=get_shipment,
        transition_mock=transition,
        update_mock=update,
        audit_mock=audit,
    )

    with pytest.raises(AgentActionExecutionError):
        await service.confirm(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            role_id=ROLE_ID,
            action_id=ACTION_ID,
        )

    repository.mark_failed.assert_awaited_once()
    update.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_is_idempotent() -> None:
    repository, get_shipment, transition, update, audit = make_mocks()
    status = next(iter(ShipmentStatus))
    cancelled = make_action(
        status="cancelled",
        expected_status=status.value,
        target_status=status.value,
    )
    repository.mark_cancelled.side_effect = [cancelled, None]
    repository.get_action.return_value = cancelled

    service = make_service(
        repository_mock=repository,
        get_shipment_mock=get_shipment,
        transition_mock=transition,
        update_mock=update,
        audit_mock=audit,
    )

    first = await service.cancel(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        action_id=ACTION_ID,
    )
    second = await service.cancel(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        action_id=ACTION_ID,
    )

    assert first.changed is True
    assert second.changed is False
