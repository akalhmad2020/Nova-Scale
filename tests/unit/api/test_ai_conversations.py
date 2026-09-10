from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.ai.application.agent.conversation import AgentExecutionResult
from app.ai.application.agent.conversation_context import ConversationContext
from app.ai.application.conversation_models import (
    ConversationDetail,
    ConversationSummary,
    PreparedConversationTurn,
    StoredConversationMessage,
)
from app.api.routes.ai import get_agent_runtime, get_conversation_service
from app.main import app
from app.modules.entitlements.api.dependencies import get_entitlements_use_case
from app.modules.identity.api.auth_dependencies import get_current_membership

TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("44444444-4444-4444-4444-444444444444")
ROLE_ID = UUID("22222222-2222-2222-2222-222222222222")
CONVERSATION_ID = UUID("55555555-5555-5555-5555-555555555555")


class FakeMembership:
    tenant_id = TENANT_ID
    user_id = USER_ID
    role_id = ROLE_ID


class FakeEntitlementSnapshot:
    def is_enabled(self, entitlement_code: str) -> bool:
        del entitlement_code
        return True


class FakeEntitlementsUseCase:
    async def execute(self, tenant_id: UUID) -> FakeEntitlementSnapshot:
        assert tenant_id == TENANT_ID
        return FakeEntitlementSnapshot()


class FakeConversationService:
    def __init__(self) -> None:
        self.completed = False
        self.rolled_back = False

    async def create(self, *, tenant_id: UUID, user_id: UUID) -> ConversationDetail:
        assert tenant_id == TENANT_ID
        assert user_id == USER_ID
        now = datetime.now(UTC)
        return ConversationDetail(
            id=CONVERSATION_ID,
            title="New conversation",
            created_at=now,
            updated_at=now,
            messages=(),
        )

    async def list(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 50,
    ) -> tuple[ConversationSummary, ...]:
        assert tenant_id == TENANT_ID
        assert user_id == USER_ID
        assert limit == 50
        now = datetime.now(UTC)
        return (
            ConversationSummary(
                id=CONVERSATION_ID,
                title="Where is SHIP-001?",
                created_at=now,
                updated_at=now,
            ),
        )

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
            title="Where is SHIP-001?",
            created_at=now,
            updated_at=now,
            messages=(
                StoredConversationMessage(
                    id=uuid4(),
                    tenant_id=TENANT_ID,
                    conversation_id=CONVERSATION_ID,
                    role="user",
                    content="Where is SHIP-001?",
                    created_at=now,
                ),
            ),
        )

    async def delete(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> None:
        assert tenant_id == TENANT_ID
        assert user_id == USER_ID
        assert conversation_id == CONVERSATION_ID

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
        assert question == "Continue"
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
        assert answer == "fake response"
        assert continuation is None
        self.completed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeAgentRuntime:
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
        assert question == "Continue"
        assert continuation is None
        assert conversation_context == ConversationContext()
        return AgentExecutionResult(answer="fake response")


FAKE_CONVERSATION_SERVICE = FakeConversationService()


def configure_overrides() -> None:
    app.dependency_overrides[get_current_membership] = lambda: FakeMembership()
    app.dependency_overrides[get_entitlements_use_case] = lambda: FakeEntitlementsUseCase()
    app.dependency_overrides[get_conversation_service] = lambda: FAKE_CONVERSATION_SERVICE
    app.dependency_overrides[get_agent_runtime] = lambda: FakeAgentRuntime()


def test_create_and_list_conversations() -> None:
    configure_overrides()

    try:
        client = TestClient(app)

        created = client.post(
            f"/api/v1/ai/tenants/{TENANT_ID}/conversations",
        )
        listed = client.get(
            f"/api/v1/ai/tenants/{TENANT_ID}/conversations",
        )

        assert created.status_code == 201
        assert created.json()["id"] == str(CONVERSATION_ID)
        assert created.json()["title"] == "New conversation"

        assert listed.status_code == 200
        assert listed.json()[0]["id"] == str(CONVERSATION_ID)
    finally:
        app.dependency_overrides.clear()


def test_get_and_delete_conversation() -> None:
    configure_overrides()

    try:
        client = TestClient(app)

        detail = client.get(
            f"/api/v1/ai/tenants/{TENANT_ID}/conversations/{CONVERSATION_ID}",
        )
        deleted = client.delete(
            f"/api/v1/ai/tenants/{TENANT_ID}/conversations/{CONVERSATION_ID}",
        )

        assert detail.status_code == 200
        assert detail.json()["messages"][0]["content"] == "Where is SHIP-001?"
        assert deleted.status_code == 204
    finally:
        app.dependency_overrides.clear()


def test_agent_uses_server_side_conversation_context() -> None:
    configure_overrides()
    FAKE_CONVERSATION_SERVICE.completed = False

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/ai/tenants/{TENANT_ID}/agent",
            json={
                "question": "Continue",
                "conversation_id": str(CONVERSATION_ID),
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "answer": "fake response",
            "continuation": None,
        }
        assert FAKE_CONVERSATION_SERVICE.completed is True
    finally:
        app.dependency_overrides.clear()
