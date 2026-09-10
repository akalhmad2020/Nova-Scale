from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.ai.application.action_exceptions import AgentActionPermissionDeniedError
from app.ai.application.agent.action_models import (
    AgentActionMutationResult,
    AgentActionProposal,
    AgentActionStatus,
    StoredAgentAction,
)
from app.ai.application.agent.conversation import AgentExecutionResult
from app.ai.application.agent.conversation_context import ConversationContext
from app.ai.application.conversation_models import (
    ConversationDetail,
    PreparedConversationTurn,
)
from app.api.routes.ai import (
    get_agent_action_service,
    get_agent_runtime,
    get_conversation_service,
)
from app.main import app
from app.modules.entitlements.api.dependencies import get_entitlements_use_case
from app.modules.identity.api.auth_dependencies import get_current_membership
from app.modules.shipments.domain.enums import ShipmentStatus

TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
ROLE_ID = UUID("33333333-3333-3333-3333-333333333333")
CONVERSATION_ID = UUID("44444444-4444-4444-4444-444444444444")
ACTION_ID = UUID("55555555-5555-5555-5555-555555555555")
SHIPMENT_ID = UUID("66666666-6666-6666-6666-666666666666")


class FakeMembership:
    tenant_id = TENANT_ID
    user_id = USER_ID
    role_id = ROLE_ID


class FakeEntitlementSnapshot:
    def is_enabled(
        self,
        entitlement_code: str,
    ) -> bool:
        del entitlement_code
        return True


class FakeEntitlementsUseCase:
    async def execute(
        self,
        tenant_id: UUID,
    ) -> FakeEntitlementSnapshot:
        assert tenant_id == TENANT_ID
        return FakeEntitlementSnapshot()


def make_action(
    *,
    status: AgentActionStatus = "pending_confirmation",
    result_summary: str | None = None,
) -> StoredAgentAction:
    now = datetime.now(UTC)
    shipment_status = next(iter(ShipmentStatus))

    return StoredAgentAction(
        id=ACTION_ID,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        conversation_id=CONVERSATION_ID,
        idempotency_key=uuid4(),
        action_type="update_shipment_notes",
        status=status,
        resource_type="shipment",
        resource_id=SHIPMENT_ID,
        shipment_identifier="SHIP-001",
        expected_status=shipment_status.value,
        expected_notes="Old notes",
        new_notes="Keep upright",
        summary="Update notes for shipment SHIP-001.",
        result_summary=result_summary,
        created_at=now,
        updated_at=now,
    )


class FakeConversationService:
    def __init__(self) -> None:
        self.completed_answers: list[str] = []
        self.rolled_back = False

    async def get(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> ConversationDetail:
        assert tenant_id == TENANT_ID
        assert user_id == USER_ID
        assert conversation_id == CONVERSATION_ID

        now = datetime.now(UTC)

        return ConversationDetail(
            id=CONVERSATION_ID,
            title="AI actions",
            created_at=now,
            updated_at=now,
            messages=(),
        )

    async def prepare_turn(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        question: str,
    ) -> PreparedConversationTurn:
        assert tenant_id == TENANT_ID
        assert user_id == USER_ID
        assert conversation_id == CONVERSATION_ID
        assert question

        return PreparedConversationTurn(
            conversation_id=conversation_id,
            conversation_context=ConversationContext(),
            continuation=None,
        )

    async def complete_turn(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        answer: str,
        continuation: object | None,
    ) -> None:
        assert tenant_id == TENANT_ID
        assert user_id == USER_ID
        assert conversation_id == CONVERSATION_ID
        assert continuation is None

        self.completed_answers.append(answer)

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeAgentActionService:
    def __init__(self) -> None:
        self.active: StoredAgentAction | None = None
        self.permission_denied = False

    async def get_active_for_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> StoredAgentAction | None:
        assert tenant_id == TENANT_ID
        assert user_id == USER_ID
        assert conversation_id == CONVERSATION_ID

        return self.active

    async def propose(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        proposal: AgentActionProposal,
    ) -> StoredAgentAction:
        assert tenant_id == TENANT_ID
        assert user_id == USER_ID
        assert conversation_id == CONVERSATION_ID
        assert proposal.action_type == "update_shipment_notes"

        self.active = make_action()

        return self.active

    async def confirm(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        role_id: UUID,
        action_id: UUID,
    ) -> AgentActionMutationResult:
        assert tenant_id == TENANT_ID
        assert user_id == USER_ID
        assert role_id == ROLE_ID
        assert action_id == ACTION_ID

        if self.permission_denied:
            raise AgentActionPermissionDeniedError

        executed = make_action(
            status="executed",
            result_summary="Shipment SHIP-001 notes were updated.",
        )

        self.active = None

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
        assert tenant_id == TENANT_ID
        assert user_id == USER_ID
        assert action_id == ACTION_ID

        cancelled = make_action(
            status="cancelled",
        )

        self.active = None

        return AgentActionMutationResult(
            action=cancelled,
            changed=True,
        )


class FakeAgentRuntime:
    def __init__(self) -> None:
        self.conversation_context: ConversationContext | None = None

    async def execute_with_context(
        self,
        *,
        tenant_id: UUID,
        role_id: UUID,
        question: str,
        continuation: object | None = None,
        conversation_context: ConversationContext | None = None,
    ) -> AgentExecutionResult:
        assert tenant_id == TENANT_ID
        assert role_id == ROLE_ID
        assert continuation is None
        assert question

        self.conversation_context = conversation_context

        shipment_status = next(iter(ShipmentStatus))

        proposal = AgentActionProposal(
            action_type="update_shipment_notes",
            shipment_id=SHIPMENT_ID,
            shipment_identifier="SHIP-001",
            expected_status=shipment_status,
            expected_notes="Old notes",
            new_notes="Keep upright",
            summary="Update notes for shipment SHIP-001.",
        )

        return AgentExecutionResult(
            answer=(
                "Update notes for shipment SHIP-001.\n\n"
                "This action changes NovaScale data and requires explicit "
                "confirmation before execution."
            ),
            continuation=None,
            action_proposal=proposal,
        )


FAKE_CONVERSATION_SERVICE = FakeConversationService()
FAKE_ACTION_SERVICE = FakeAgentActionService()
FAKE_AGENT_RUNTIME = FakeAgentRuntime()


def configure_overrides() -> None:
    app.dependency_overrides[get_current_membership] = lambda: FakeMembership()

    app.dependency_overrides[get_entitlements_use_case] = lambda: FakeEntitlementsUseCase()

    app.dependency_overrides[get_conversation_service] = lambda: FAKE_CONVERSATION_SERVICE

    app.dependency_overrides[get_agent_action_service] = lambda: FAKE_ACTION_SERVICE

    app.dependency_overrides[get_agent_runtime] = lambda: FAKE_AGENT_RUNTIME


def reset_fakes() -> None:
    FAKE_ACTION_SERVICE.active = None
    FAKE_ACTION_SERVICE.permission_denied = False

    FAKE_CONVERSATION_SERVICE.completed_answers.clear()
    FAKE_CONVERSATION_SERVICE.rolled_back = False

    FAKE_AGENT_RUNTIME.conversation_context = None


def test_agent_proposal_is_persisted_and_visible_on_conversation() -> None:
    configure_overrides()
    reset_fakes()

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/ai/tenants/{TENANT_ID}/agent",
            json={
                "question": "Set SHIP-001 notes to Keep upright",
                "conversation_id": str(CONVERSATION_ID),
            },
        )

        assert response.status_code == 200
        assert response.json()["continuation"] is None
        assert FAKE_ACTION_SERVICE.active is not None

        assert FAKE_AGENT_RUNTIME.conversation_context == ConversationContext(
            messages=(),
        )

        detail = client.get(
            f"/api/v1/ai/tenants/{TENANT_ID}/conversations/{CONVERSATION_ID}",
        )

        assert detail.status_code == 200

        assert detail.json()["pending_action"]["id"] == str(
            ACTION_ID,
        )

        assert detail.json()["pending_action"]["status"] == "pending_confirmation"
    finally:
        app.dependency_overrides.clear()


def test_confirm_action_records_execution_message() -> None:
    configure_overrides()
    reset_fakes()

    FAKE_ACTION_SERVICE.active = make_action()

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/ai/tenants/{TENANT_ID}/actions/{ACTION_ID}/confirm",
        )

        assert response.status_code == 200

        assert response.json()["action"]["status"] == "executed"

        assert response.json()["answer"] == ("Shipment SHIP-001 notes were updated.")

        assert FAKE_CONVERSATION_SERVICE.completed_answers[-1] == (
            "Shipment SHIP-001 notes were updated."
        )
    finally:
        app.dependency_overrides.clear()


def test_cancel_action_records_cancellation_message() -> None:
    configure_overrides()
    reset_fakes()

    FAKE_ACTION_SERVICE.active = make_action()

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/ai/tenants/{TENANT_ID}/actions/{ACTION_ID}/cancel",
        )

        assert response.status_code == 200

        assert response.json()["action"]["status"] == "cancelled"

        assert "Cancelled pending AI action" in response.json()["answer"]
    finally:
        app.dependency_overrides.clear()


def test_confirm_action_rechecks_permission() -> None:
    configure_overrides()
    reset_fakes()

    FAKE_ACTION_SERVICE.active = make_action()
    FAKE_ACTION_SERVICE.permission_denied = True

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/ai/tenants/{TENANT_ID}/actions/{ACTION_ID}/confirm",
        )

        assert response.status_code == 403

        assert response.json() == {
            "detail": "Permission denied for this AI action",
        }
    finally:
        app.dependency_overrides.clear()


def test_stateless_agent_write_action_is_rejected() -> None:
    configure_overrides()
    reset_fakes()

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/ai/tenants/{TENANT_ID}/agent",
            json={
                "question": "Set SHIP-001 notes to Keep upright",
            },
        )

        assert FAKE_AGENT_RUNTIME.conversation_context is None

        assert response.status_code == 409

        assert response.json() == {
            "detail": (
                "AI write actions require a persistent conversation "
                "so confirmation can be recorded safely"
            )
        }
    finally:
        app.dependency_overrides.clear()
