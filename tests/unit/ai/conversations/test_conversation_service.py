from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.ai.application.agent.conversation import AgentContinuation
from app.ai.application.conversation_exceptions import ConversationNotFoundError
from app.ai.application.conversation_models import (
    StoredConversation,
    StoredConversationMessage,
)
from app.ai.application.services.conversation_service import (
    MAX_CONTEXT_MESSAGES,
    ConversationService,
)


class FakeConversationRepository:
    def __init__(self) -> None:
        self.conversations: dict[UUID, StoredConversation] = {}
        self.messages: list[StoredConversationMessage] = []
        self.commits = 0
        self.rollbacks = 0

    async def create_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        title: str,
    ) -> StoredConversation:
        now = datetime.now(UTC)
        conversation = StoredConversation(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        self.conversations[conversation.id] = conversation
        return conversation

    async def get_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> StoredConversation | None:
        conversation = self.conversations.get(conversation_id)

        if conversation is None:
            return None

        if conversation.tenant_id != tenant_id or conversation.user_id != user_id:
            return None

        return conversation

    async def list_conversations(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        limit: int,
    ) -> tuple[StoredConversation, ...]:
        matches = [
            item
            for item in self.conversations.values()
            if item.tenant_id == tenant_id and item.user_id == user_id
        ]
        matches.sort(key=lambda item: item.updated_at, reverse=True)
        return tuple(matches[:limit])

    async def list_messages(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> tuple[StoredConversationMessage, ...]:
        if (
            await self.get_conversation(
                tenant_id=tenant_id,
                user_id=user_id,
                conversation_id=conversation_id,
            )
            is None
        ):
            return ()

        return tuple(
            message
            for message in self.messages
            if message.tenant_id == tenant_id and message.conversation_id == conversation_id
        )

    async def list_recent_messages(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        limit: int,
    ) -> tuple[StoredConversationMessage, ...]:
        messages = await self.list_messages(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        return messages[-limit:]

    async def add_message(
        self,
        *,
        tenant_id: UUID,
        conversation_id: UUID,
        role: str,
        content: str,
    ) -> StoredConversationMessage:
        message = StoredConversationMessage(
            id=uuid4(),
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=role,  # type: ignore[arg-type]
            content=content,
            created_at=datetime.now(UTC),
        )
        self.messages.append(message)
        return message

    async def update_title(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        title: str,
    ) -> None:
        conversation = await self.get_conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        assert conversation is not None
        self.conversations[conversation_id] = StoredConversation(
            id=conversation.id,
            tenant_id=conversation.tenant_id,
            user_id=conversation.user_id,
            title=title,
            created_at=conversation.created_at,
            updated_at=datetime.now(UTC),
            continuation_kind=conversation.continuation_kind,
            continuation_route=conversation.continuation_route,
            continuation_original_identifier=(conversation.continuation_original_identifier),
        )

    async def set_continuation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        continuation: AgentContinuation | None,
    ) -> None:
        conversation = await self.get_conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        assert conversation is not None

        self.conversations[conversation_id] = StoredConversation(
            id=conversation.id,
            tenant_id=conversation.tenant_id,
            user_id=conversation.user_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=datetime.now(UTC),
            continuation_kind=(continuation.kind if continuation else None),
            continuation_route=(continuation.route if continuation else None),
            continuation_original_identifier=(
                continuation.original_identifier if continuation else None
            ),
        )

    async def delete_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> bool:
        conversation = await self.get_conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if conversation is None:
            return False

        del self.conversations[conversation_id]
        return True

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_conversation_service_creates_and_lists_user_conversations() -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    repository = FakeConversationRepository()
    service = ConversationService(repository=repository)

    created = await service.create(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    conversations = await service.list(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    assert created.title == "New conversation"
    assert created.messages == ()
    assert len(conversations) == 1
    assert conversations[0].id == created.id
    assert repository.commits == 1


@pytest.mark.asyncio
async def test_prepare_turn_uses_only_recent_history_and_updates_first_title() -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    repository = FakeConversationRepository()
    service = ConversationService(repository=repository)

    created = await service.create(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    base_time = datetime.now(UTC) - timedelta(hours=1)

    for index in range(MAX_CONTEXT_MESSAGES + 5):
        repository.messages.append(
            StoredConversationMessage(
                id=uuid4(),
                tenant_id=tenant_id,
                conversation_id=created.id,
                role="user" if index % 2 == 0 else "assistant",
                content=f"Message {index}",
                created_at=base_time + timedelta(minutes=index),
            )
        )

    turn = await service.prepare_turn(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=created.id,
        question="Where is SHIP-001?",
    )

    assert len(turn.conversation_context.messages) == MAX_CONTEXT_MESSAGES
    assert turn.conversation_context.messages[0].content == "Message 5"
    assert turn.conversation_context.messages[-1].content == "Message 24"
    assert repository.messages[-1].content == "Where is SHIP-001?"


@pytest.mark.asyncio
async def test_complete_turn_persists_answer_and_continuation() -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    repository = FakeConversationRepository()
    service = ConversationService(repository=repository)

    created = await service.create(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    await service.prepare_turn(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=created.id,
        question="Where is ORDER-100?",
    )

    continuation = AgentContinuation(
        kind="shipment_selection",
        route="get_shipment",
        original_identifier="ORDER-100",
    )

    await service.complete_turn(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=created.id,
        answer="Please provide a tracking number.",
        continuation=continuation,
    )

    detail = await service.get(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=created.id,
    )

    assert [message.role for message in detail.messages] == [
        "user",
        "assistant",
    ]
    assert detail.continuation == continuation
    assert repository.commits == 2


@pytest.mark.asyncio
async def test_conversation_service_enforces_user_ownership() -> None:
    tenant_id = uuid4()
    repository = FakeConversationRepository()
    service = ConversationService(repository=repository)

    created = await service.create(
        tenant_id=tenant_id,
        user_id=uuid4(),
    )

    with pytest.raises(ConversationNotFoundError):
        await service.get(
            tenant_id=tenant_id,
            user_id=uuid4(),
            conversation_id=created.id,
        )


@pytest.mark.asyncio
async def test_delete_missing_conversation_rolls_back() -> None:
    repository = FakeConversationRepository()
    service = ConversationService(repository=repository)

    with pytest.raises(ConversationNotFoundError):
        await service.delete(
            tenant_id=uuid4(),
            user_id=uuid4(),
            conversation_id=uuid4(),
        )

    assert repository.rollbacks == 1
