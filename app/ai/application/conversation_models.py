from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.ai.application.agent.conversation import AgentContinuation
from app.ai.application.agent.conversation_context import ConversationContext, ConversationRole


@dataclass(frozen=True, slots=True)
class StoredConversation:
    id: UUID
    tenant_id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    continuation_kind: str | None = None
    continuation_route: str | None = None
    continuation_original_identifier: str | None = None


@dataclass(frozen=True, slots=True)
class StoredConversationMessage:
    id: UUID
    tenant_id: UUID
    conversation_id: UUID
    role: ConversationRole
    content: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ConversationSummary:
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ConversationDetail:
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: tuple[StoredConversationMessage, ...]
    continuation: AgentContinuation | None = None


@dataclass(frozen=True, slots=True)
class PreparedConversationTurn:
    conversation_id: UUID
    conversation_context: ConversationContext
    continuation: AgentContinuation | None
