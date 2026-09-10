from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.agent.action_models import AgentActionProposal
from app.ai.infrastructure.actions.repository import SQLAlchemyAgentActionRepository
from app.ai.infrastructure.conversations.repository import (
    SQLAlchemyConversationRepository,
)
from app.modules.identity.domain.enums import TenantStatus
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.shipments.domain.enums import ShipmentStatus

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
        name=f"AI Action Tenant {tenant_id}",
        slug=f"ai-action-{tenant_id}",
        status=TenantStatus.ACTIVE,
    )
    tenant.id = tenant_id

    user = User(
        email=f"ai-action-{user_id}@example.com",
        password_hash="not-used-in-this-test",
        first_name="AI",
        last_name="Action",
        is_active=True,
    )
    user.id = user_id

    session.add_all([tenant, user])
    await session.flush()


async def create_conversation(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
) -> UUID:
    conversation = await SQLAlchemyConversationRepository(session).create_conversation(
        tenant_id=tenant_id,
        user_id=user_id,
        title="Action conversation",
    )
    return conversation.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_action_repository_persists_pending_action(
    db_session: AsyncSession,
    set_tenant_context: SetTenantContext,
) -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    shipment_id = uuid4()

    await create_tenant_and_user(
        session=db_session,
        set_tenant_context=set_tenant_context,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    conversation_id = await create_conversation(
        session=db_session,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    status = next(iter(ShipmentStatus))
    repository = SQLAlchemyAgentActionRepository(db_session)

    created = await repository.create_action(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
        idempotency_key=uuid4(),
        proposal=AgentActionProposal(
            action_type="update_shipment_notes",
            shipment_id=shipment_id,
            shipment_identifier="SHIP-001",
            expected_status=status,
            expected_notes="Old notes",
            new_notes="Keep upright",
            summary="Update shipment notes",
        ),
    )

    active = await repository.get_active_for_conversation(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    assert active is not None
    assert active.id == created.id
    assert active.status == "pending_confirmation"
    assert active.new_notes == "Keep upright"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_action_repository_enforces_user_ownership(
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
        email=f"ai-action-{other_user_id}@example.com",
        password_hash="not-used-in-this-test",
        first_name="Other",
        last_name="User",
        is_active=True,
    )
    other_user.id = other_user_id
    db_session.add(other_user)
    await db_session.flush()

    conversation_id = await create_conversation(
        session=db_session,
        tenant_id=tenant_id,
        user_id=owner_id,
    )

    status = next(iter(ShipmentStatus))
    repository = SQLAlchemyAgentActionRepository(db_session)
    created = await repository.create_action(
        tenant_id=tenant_id,
        user_id=owner_id,
        conversation_id=conversation_id,
        idempotency_key=uuid4(),
        proposal=AgentActionProposal(
            action_type="update_shipment_notes",
            shipment_id=uuid4(),
            shipment_identifier="SHIP-001",
            expected_status=status,
            expected_notes=None,
            new_notes="Private notes",
            summary="Update shipment notes",
        ),
    )

    hidden = await repository.get_action(
        tenant_id=tenant_id,
        user_id=other_user_id,
        action_id=created.id,
    )

    assert hidden is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_action_repository_respects_tenant_rls(
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
    conversation_id = await create_conversation(
        session=db_session,
        tenant_id=tenant_a,
        user_id=user_a,
    )

    status = next(iter(ShipmentStatus))
    repository = SQLAlchemyAgentActionRepository(db_session)
    created = await repository.create_action(
        tenant_id=tenant_a,
        user_id=user_a,
        conversation_id=conversation_id,
        idempotency_key=uuid4(),
        proposal=AgentActionProposal(
            action_type="update_shipment_notes",
            shipment_id=uuid4(),
            shipment_identifier="SHIP-A",
            expected_status=status,
            expected_notes=None,
            new_notes="Tenant A only",
            summary="Update shipment notes",
        ),
    )

    await create_tenant_and_user(
        session=db_session,
        set_tenant_context=set_tenant_context,
        tenant_id=tenant_b,
        user_id=user_b,
    )

    hidden = await repository.get_action(
        tenant_id=tenant_a,
        user_id=user_a,
        action_id=created.id,
    )

    assert hidden is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_action_repository_claim_is_single_use(
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
    conversation_id = await create_conversation(
        session=db_session,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    statuses = list(ShipmentStatus)
    current = statuses[0]
    target = next(item for item in statuses if item != current)
    repository = SQLAlchemyAgentActionRepository(db_session)

    created = await repository.create_action(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
        idempotency_key=uuid4(),
        proposal=AgentActionProposal(
            action_type="transition_shipment_status",
            shipment_id=uuid4(),
            shipment_identifier="SHIP-001",
            expected_status=current,
            target_status=target,
            summary="Transition shipment",
        ),
    )

    first_claim = await repository.claim_for_execution(
        tenant_id=tenant_id,
        user_id=user_id,
        action_id=created.id,
    )
    second_claim = await repository.claim_for_execution(
        tenant_id=tenant_id,
        user_id=user_id,
        action_id=created.id,
    )

    assert first_claim is not None
    assert first_claim.status == "executing"
    assert second_claim is None
