from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.infrastructure.conversations.repository import (
    SQLAlchemyConversationRepository,
)
from app.modules.identity.domain.enums import TenantStatus
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User

SetTenantContext = Callable[[UUID], Awaitable[None]]


async def create_tenant_and_user(
    *,
    session: AsyncSession,
    set_tenant_context: SetTenantContext,
    tenant_id: UUID,
    user_id: UUID,
) -> None:
    await set_tenant_context(tenant_id)

    tenant = Tenant(
        name=f"AI Conversation Tenant {tenant_id}",
        slug=f"ai-conversation-{tenant_id}",
        status=TenantStatus.ACTIVE,
    )
    tenant.id = tenant_id

    user = User(
        email=f"ai-conversation-{user_id}@example.com",
        password_hash="not-used-in-this-test",
        first_name="AI",
        last_name="Tester",
        is_active=True,
    )
    user.id = user_id

    session.add_all([tenant, user])
    await session.flush()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_conversation_repository_persists_messages_and_history(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    tenant_id = uuid4()
    user_id = uuid4()

    await create_tenant_and_user(
        session=db_session,
        set_tenant_context=set_tenant_context,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    repository = SQLAlchemyConversationRepository(db_session)

    conversation = await repository.create_conversation(
        tenant_id=tenant_id,
        user_id=user_id,
        title="New conversation",
    )

    await repository.add_message(
        tenant_id=tenant_id,
        conversation_id=conversation.id,
        role="user",
        content="Where is SHIP-001?",
    )
    await repository.add_message(
        tenant_id=tenant_id,
        conversation_id=conversation.id,
        role="assistant",
        content="SHIP-001 is in transit.",
    )

    messages = await repository.list_messages(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation.id,
    )

    assert [message.role for message in messages] == [
        "user",
        "assistant",
    ]
    assert [message.content for message in messages] == [
        "Where is SHIP-001?",
        "SHIP-001 is in transit.",
    ]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_conversation_repository_enforces_user_ownership(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    tenant_id = uuid4()
    owner_id = uuid4()
    other_user_id = uuid4()

    await create_tenant_and_user(
        session=db_session,
        set_tenant_context=set_tenant_context,
        tenant_id=tenant_id,
        user_id=owner_id,
    )

    other_user = User(
        email=f"ai-conversation-{other_user_id}@example.com",
        password_hash="not-used-in-this-test",
        first_name="Other",
        last_name="User",
        is_active=True,
    )
    other_user.id = other_user_id
    db_session.add(other_user)
    await db_session.flush()

    repository = SQLAlchemyConversationRepository(db_session)
    conversation = await repository.create_conversation(
        tenant_id=tenant_id,
        user_id=owner_id,
        title="Private conversation",
    )

    hidden = await repository.get_conversation(
        tenant_id=tenant_id,
        user_id=other_user_id,
        conversation_id=conversation.id,
    )

    assert hidden is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_conversation_repository_respects_tenant_rls(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    user_a = uuid4()
    user_b = uuid4()

    await create_tenant_and_user(
        session=db_session,
        set_tenant_context=set_tenant_context,
        tenant_id=tenant_a,
        user_id=user_a,
    )

    repository = SQLAlchemyConversationRepository(db_session)
    conversation = await repository.create_conversation(
        tenant_id=tenant_a,
        user_id=user_a,
        title="Tenant A conversation",
    )

    await create_tenant_and_user(
        session=db_session,
        set_tenant_context=set_tenant_context,
        tenant_id=tenant_b,
        user_id=user_b,
    )

    hidden = await repository.get_conversation(
        tenant_id=tenant_a,
        user_id=user_a,
        conversation_id=conversation.id,
    )

    assert hidden is None
