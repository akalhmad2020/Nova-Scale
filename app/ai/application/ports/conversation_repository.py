from typing import Protocol
from uuid import UUID

from app.ai.application.agent.conversation import AgentContinuation
from app.ai.application.agent.conversation_context import ConversationRole
from app.ai.application.conversation_models import (
    StoredConversation,
    StoredConversationMessage,
)


class ConversationRepository(Protocol):
    async def create_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        title: str,
    ) -> StoredConversation: ...

    async def get_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> StoredConversation | None: ...

    async def list_conversations(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        limit: int,
    ) -> tuple[StoredConversation, ...]: ...

    async def list_messages(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> tuple[StoredConversationMessage, ...]: ...

    async def list_recent_messages(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        limit: int,
    ) -> tuple[StoredConversationMessage, ...]: ...

    async def add_message(
        self,
        *,
        tenant_id: UUID,
        conversation_id: UUID,
        role: ConversationRole,
        content: str,
    ) -> StoredConversationMessage: ...

    async def update_title(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        title: str,
    ) -> None: ...

    async def set_continuation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        continuation: AgentContinuation | None,
    ) -> None: ...

    async def delete_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> bool: ...

    async def flush(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
