from typing import Protocol
from uuid import UUID

from app.ai.application.agent.action_models import (
    AgentActionProposal,
    StoredAgentAction,
)


class AgentActionRepository(Protocol):
    async def create_action(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        idempotency_key: UUID,
        proposal: AgentActionProposal,
    ) -> StoredAgentAction: ...

    async def get_action(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
    ) -> StoredAgentAction | None: ...

    async def get_active_for_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> StoredAgentAction | None: ...

    async def claim_for_execution(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
    ) -> StoredAgentAction | None: ...

    async def mark_executed(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
        result_summary: str,
    ) -> StoredAgentAction: ...

    async def mark_cancelled(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
    ) -> StoredAgentAction | None: ...

    async def mark_failed(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
        failure_reason: str,
    ) -> StoredAgentAction: ...

    async def flush(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
