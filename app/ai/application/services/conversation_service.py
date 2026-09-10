from typing import cast
from uuid import UUID

from app.ai.application.agent.conversation import (
    AgentContinuation,
    ShipmentContinuationRoute,
)
from app.ai.application.agent.conversation_context import (
    ConversationContext,
    ConversationMessage,
)
from app.ai.application.conversation_exceptions import ConversationNotFoundError
from app.ai.application.conversation_models import (
    ConversationDetail,
    ConversationSummary,
    PreparedConversationTurn,
    StoredConversation,
    StoredConversationMessage,
)
from app.ai.application.ports.conversation_repository import ConversationRepository

MAX_CONTEXT_MESSAGES = 20
DEFAULT_CONVERSATION_TITLE = "New conversation"
MAX_CONVERSATION_TITLE_LENGTH = 120


class ConversationService:
    def __init__(
        self,
        *,
        repository: ConversationRepository,
    ) -> None:
        self._repository = repository

    async def create(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ConversationDetail:
        conversation = await self._repository.create_conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            title=DEFAULT_CONVERSATION_TITLE,
        )
        await self._repository.commit()

        return self._to_detail(
            conversation,
            messages=(),
        )

    async def list(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 50,
    ) -> tuple[ConversationSummary, ...]:
        conversations = await self._repository.list_conversations(
            tenant_id=tenant_id,
            user_id=user_id,
            limit=limit,
        )

        return tuple(
            ConversationSummary(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
            for conversation in conversations
        )

    async def get(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> ConversationDetail:
        conversation = await self._require_conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        messages = await self._repository.list_messages(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        return self._to_detail(
            conversation,
            messages=messages,
        )

    async def delete(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> None:
        deleted = await self._repository.delete_conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if not deleted:
            await self._repository.rollback()
            raise ConversationNotFoundError

        await self._repository.commit()

    async def prepare_turn(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        question: str,
    ) -> PreparedConversationTurn:
        conversation = await self._require_conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        recent_messages = await self._repository.list_recent_messages(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            limit=MAX_CONTEXT_MESSAGES,
        )

        conversation_context = ConversationContext(
            messages=tuple(
                ConversationMessage(
                    role=message.role,
                    content=message.content,
                )
                for message in recent_messages
            )
        )

        if not recent_messages and conversation.title == DEFAULT_CONVERSATION_TITLE:
            await self._repository.update_title(
                tenant_id=tenant_id,
                user_id=user_id,
                conversation_id=conversation_id,
                title=self._build_title(question),
            )

        await self._repository.add_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role="user",
            content=question,
        )
        await self._repository.flush()

        return PreparedConversationTurn(
            conversation_id=conversation_id,
            conversation_context=conversation_context,
            continuation=self._build_continuation(conversation),
        )

    async def complete_turn(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        answer: str,
        continuation: AgentContinuation | None,
    ) -> None:
        await self._repository.add_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
        )

        await self._repository.set_continuation(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            continuation=continuation,
        )

        await self._repository.commit()

    async def rollback(self) -> None:
        await self._repository.rollback()

    async def _require_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> StoredConversation:
        conversation = await self._repository.get_conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if conversation is None:
            raise ConversationNotFoundError

        return conversation

    @staticmethod
    def _build_title(question: str) -> str:
        normalized = " ".join(question.split())

        if len(normalized) <= MAX_CONVERSATION_TITLE_LENGTH:
            return normalized

        return normalized[: MAX_CONVERSATION_TITLE_LENGTH - 1].rstrip() + "…"

    @staticmethod
    def _build_continuation(
        conversation: StoredConversation,
    ) -> AgentContinuation | None:
        if conversation.continuation_kind != "shipment_selection":
            return None

        route = conversation.continuation_route
        original_identifier = conversation.continuation_original_identifier

        if route is None or original_identifier is None:
            return None

        if route not in {
            "get_shipment",
            "summarize_shipment",
            "analyze_shipment_operations",
        }:
            return None

        return AgentContinuation(
            kind="shipment_selection",
            route=cast(ShipmentContinuationRoute, route),
            original_identifier=original_identifier,
        )

    @classmethod
    def _to_detail(
        cls,
        conversation: StoredConversation,
        *,
        messages: tuple[StoredConversationMessage, ...],
    ) -> ConversationDetail:
        return ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=messages,
            continuation=cls._build_continuation(conversation),
        )
