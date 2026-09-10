from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.agent.conversation import AgentContinuation
from app.ai.application.agent.conversation_context import ConversationRole
from app.ai.application.conversation_models import (
    StoredConversation,
    StoredConversationMessage,
)
from app.ai.infrastructure.conversations.models import (
    AIConversation,
    AIConversationMessage,
)


class SQLAlchemyConversationRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def create_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        title: str,
    ) -> StoredConversation:
        model = AIConversation(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
        )

        self._session.add(model)
        await self._session.flush()

        return self._conversation_record(model)

    async def get_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> StoredConversation | None:
        model = await self._get_model(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if model is None:
            return None

        return self._conversation_record(model)

    async def list_conversations(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        limit: int,
    ) -> tuple[StoredConversation, ...]:
        result = await self._session.scalars(
            select(AIConversation)
            .where(
                AIConversation.tenant_id == tenant_id,
                AIConversation.user_id == user_id,
                AIConversation.deleted_at.is_(None),
            )
            .order_by(
                AIConversation.updated_at.desc(),
                AIConversation.id.desc(),
            )
            .limit(limit)
        )

        return tuple(self._conversation_record(model) for model in result.all())

    async def list_messages(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> tuple[StoredConversationMessage, ...]:
        conversation = await self._get_model(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if conversation is None:
            return ()

        result = await self._session.scalars(
            select(AIConversationMessage)
            .where(
                AIConversationMessage.tenant_id == tenant_id,
                AIConversationMessage.conversation_id == conversation_id,
            )
            .order_by(
                AIConversationMessage.created_at.asc(),
                AIConversationMessage.id.asc(),
            )
        )

        return tuple(self._message_record(model) for model in result.all())

    async def list_recent_messages(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        limit: int,
    ) -> tuple[StoredConversationMessage, ...]:
        conversation = await self._get_model(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if conversation is None:
            return ()

        result = await self._session.scalars(
            select(AIConversationMessage)
            .where(
                AIConversationMessage.tenant_id == tenant_id,
                AIConversationMessage.conversation_id == conversation_id,
            )
            .order_by(
                AIConversationMessage.created_at.desc(),
                AIConversationMessage.id.desc(),
            )
            .limit(limit)
        )

        messages = [self._message_record(model) for model in result.all()]

        messages.reverse()

        return tuple(messages)

    async def add_message(
        self,
        *,
        tenant_id: UUID,
        conversation_id: UUID,
        role: ConversationRole,
        content: str,
    ) -> StoredConversationMessage:
        model = AIConversationMessage(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
        )

        self._session.add(model)
        await self._session.flush()

        return self._message_record(model)

    async def update_title(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        title: str,
    ) -> None:
        model = await self._get_model(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if model is None:
            return

        model.title = title
        model.updated_at = datetime.now(UTC)

    async def set_continuation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        continuation: AgentContinuation | None,
    ) -> None:
        model = await self._get_model(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if model is None:
            return

        if continuation is None:
            model.continuation_kind = None
            model.continuation_route = None
            model.continuation_original_identifier = None
        else:
            model.continuation_kind = continuation.kind
            model.continuation_route = continuation.route
            model.continuation_original_identifier = continuation.original_identifier

        model.updated_at = datetime.now(UTC)

    async def delete_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> bool:
        model = await self._get_model(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if model is None:
            return False

        now = datetime.now(UTC)

        model.deleted_at = now
        model.updated_at = now

        return True

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def _get_model(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> AIConversation | None:
        return cast(
            AIConversation | None,
            await self._session.scalar(
                select(AIConversation).where(
                    AIConversation.id == conversation_id,
                    AIConversation.tenant_id == tenant_id,
                    AIConversation.user_id == user_id,
                    AIConversation.deleted_at.is_(None),
                )
            ),
        )

    @staticmethod
    def _conversation_record(
        model: AIConversation,
    ) -> StoredConversation:
        return StoredConversation(
            id=model.id,
            tenant_id=model.tenant_id,
            user_id=model.user_id,
            title=model.title,
            created_at=model.created_at,
            updated_at=model.updated_at,
            continuation_kind=model.continuation_kind,
            continuation_route=model.continuation_route,
            continuation_original_identifier=(model.continuation_original_identifier),
        )

    @staticmethod
    def _message_record(
        model: AIConversationMessage,
    ) -> StoredConversationMessage:
        return StoredConversationMessage(
            id=model.id,
            tenant_id=model.tenant_id,
            conversation_id=model.conversation_id,
            role=cast(
                ConversationRole,
                model.role,
            ),
            content=model.content,
            created_at=model.created_at,
        )
