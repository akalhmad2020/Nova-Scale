from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.agent.action_models import (
    AgentActionProposal,
    AgentActionStatus,
    AgentActionType,
    StoredAgentAction,
)
from app.ai.infrastructure.actions.models import AIAgentAction

ACTIVE_ACTION_STATUSES = (
    "pending_confirmation",
    "executing",
)


class SQLAlchemyAgentActionRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def create_action(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        idempotency_key: UUID,
        proposal: AgentActionProposal,
    ) -> StoredAgentAction:
        model = AIAgentAction(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            idempotency_key=idempotency_key,
            action_type=proposal.action_type,
            status="pending_confirmation",
            resource_type="shipment",
            resource_id=proposal.shipment_id,
            shipment_identifier=proposal.shipment_identifier,
            expected_status=proposal.expected_status.value,
            target_status=(
                proposal.target_status.value if proposal.target_status is not None else None
            ),
            expected_notes=proposal.expected_notes,
            new_notes=proposal.new_notes,
            summary=proposal.summary,
        )

        self._session.add(model)
        await self._session.flush()

        return self._record(model)

    async def get_action(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
    ) -> StoredAgentAction | None:
        model = cast(
            AIAgentAction | None,
            await self._session.scalar(
                select(AIAgentAction).where(
                    AIAgentAction.id == action_id,
                    AIAgentAction.tenant_id == tenant_id,
                    AIAgentAction.user_id == user_id,
                )
            ),
        )

        if model is None:
            return None

        return self._record(model)

    async def get_active_for_conversation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
    ) -> StoredAgentAction | None:
        model = cast(
            AIAgentAction | None,
            await self._session.scalar(
                select(AIAgentAction)
                .where(
                    AIAgentAction.tenant_id == tenant_id,
                    AIAgentAction.user_id == user_id,
                    AIAgentAction.conversation_id == conversation_id,
                    AIAgentAction.status.in_(ACTIVE_ACTION_STATUSES),
                )
                .order_by(AIAgentAction.created_at.desc())
                .limit(1)
            ),
        )

        if model is None:
            return None

        return self._record(model)

    async def claim_for_execution(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
    ) -> StoredAgentAction | None:
        now = datetime.now(UTC)

        model = cast(
            AIAgentAction | None,
            await self._session.scalar(
                update(AIAgentAction)
                .where(
                    AIAgentAction.id == action_id,
                    AIAgentAction.tenant_id == tenant_id,
                    AIAgentAction.user_id == user_id,
                    AIAgentAction.status == "pending_confirmation",
                )
                .values(
                    status="executing",
                    confirmed_at=now,
                    updated_at=now,
                )
                .returning(AIAgentAction)
            ),
        )

        if model is None:
            return None

        return self._record(model)

    async def mark_executed(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
        result_summary: str,
    ) -> StoredAgentAction:
        now = datetime.now(UTC)

        model = cast(
            AIAgentAction | None,
            await self._session.scalar(
                update(AIAgentAction)
                .where(
                    AIAgentAction.id == action_id,
                    AIAgentAction.tenant_id == tenant_id,
                    AIAgentAction.user_id == user_id,
                    AIAgentAction.status == "executing",
                )
                .values(
                    status="executed",
                    result_summary=result_summary,
                    executed_at=now,
                    updated_at=now,
                )
                .returning(AIAgentAction)
            ),
        )

        if model is None:
            raise RuntimeError("Executing AI action could not be marked executed")

        return self._record(model)

    async def mark_cancelled(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
    ) -> StoredAgentAction | None:
        now = datetime.now(UTC)

        model = cast(
            AIAgentAction | None,
            await self._session.scalar(
                update(AIAgentAction)
                .where(
                    AIAgentAction.id == action_id,
                    AIAgentAction.tenant_id == tenant_id,
                    AIAgentAction.user_id == user_id,
                    AIAgentAction.status == "pending_confirmation",
                )
                .values(
                    status="cancelled",
                    cancelled_at=now,
                    updated_at=now,
                )
                .returning(AIAgentAction)
            ),
        )

        if model is None:
            return None

        return self._record(model)

    async def mark_failed(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        action_id: UUID,
        failure_reason: str,
    ) -> StoredAgentAction:
        now = datetime.now(UTC)

        model = cast(
            AIAgentAction | None,
            await self._session.scalar(
                update(AIAgentAction)
                .where(
                    AIAgentAction.id == action_id,
                    AIAgentAction.tenant_id == tenant_id,
                    AIAgentAction.user_id == user_id,
                    AIAgentAction.status == "executing",
                )
                .values(
                    status="failed",
                    failure_reason=failure_reason,
                    failed_at=now,
                    updated_at=now,
                )
                .returning(AIAgentAction)
            ),
        )

        if model is None:
            raise RuntimeError("Executing AI action could not be marked failed")

        return self._record(model)

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    @staticmethod
    def _record(model: AIAgentAction) -> StoredAgentAction:
        return StoredAgentAction(
            id=model.id,
            tenant_id=model.tenant_id,
            user_id=model.user_id,
            conversation_id=model.conversation_id,
            idempotency_key=model.idempotency_key,
            action_type=cast(AgentActionType, model.action_type),
            status=cast(AgentActionStatus, model.status),
            resource_type=model.resource_type,
            resource_id=model.resource_id,
            shipment_identifier=model.shipment_identifier,
            expected_status=model.expected_status,
            target_status=model.target_status,
            expected_notes=model.expected_notes,
            new_notes=model.new_notes,
            summary=model.summary,
            result_summary=model.result_summary,
            failure_reason=model.failure_reason,
            confirmed_at=model.confirmed_at,
            executed_at=model.executed_at,
            cancelled_at=model.cancelled_at,
            failed_at=model.failed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
