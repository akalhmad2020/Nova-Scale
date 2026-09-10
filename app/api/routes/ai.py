from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.action_exceptions import (
    AgentActionConflictError,
    AgentActionExecutionError,
    AgentActionInProgressError,
    AgentActionNotFoundError,
    AgentActionPermissionDeniedError,
    PendingAgentActionExistsError,
)
from app.ai.application.agent.action_models import (
    AgentActionStatus,
    AgentActionType,
    StoredAgentAction,
)
from app.ai.application.agent.conversation import (
    AgentContinuation,
    AgentContinuationKind,
    ShipmentContinuationRoute,
)
from app.ai.application.agent.conversation_context import (
    ConversationContext,
    ConversationMessage,
)
from app.ai.application.agent.shipment_operational_models import (
    OperationalRiskLevel,
    OperationalSeverity,
)
from app.ai.application.agent.shipment_resolution_exceptions import (
    ShipmentIdentifierAmbiguousError,
)
from app.ai.application.agent.shipment_resolution_models import ShipmentIdentifierKind
from app.ai.application.conversation_exceptions import ConversationNotFoundError
from app.ai.application.conversation_models import ConversationDetail, ConversationSummary
from app.ai.application.dependencies import (
    build_agent_action_service,
    build_agent_runtime,
    build_analyze_shipment_service,
    build_answer_question_service,
    build_conversation_service,
    build_resolve_shipment_service,
)
from app.ai.application.services.agent_action_service import AgentActionService
from app.ai.application.services.analyze_shipment import AnalyzeShipmentService
from app.ai.application.services.answer_question import AnswerQuestionService
from app.ai.application.services.conversation_service import ConversationService
from app.ai.application.services.resolve_shipment import ResolveShipmentService
from app.ai.infrastructure.agent.langgraph_runtime import LangGraphAgentRuntime
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.modules.entitlements.api.dependencies import require_entitlement
from app.modules.entitlements.domain.catalog import Entitlements
from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.shipments.application.exceptions import ShipmentNotFoundError

router = APIRouter(prefix="/ai", tags=["ai"])


class AskQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=5, ge=1, le=20)


class RAGSourceResponse(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    score: float


class AskQuestionResponse(BaseModel):
    content: str
    model: str
    sources: list[RAGSourceResponse]


class AgentContinuationRequest(BaseModel):
    kind: AgentContinuationKind
    route: ShipmentContinuationRoute
    original_identifier: str = Field(min_length=1, max_length=500)


class ConversationMessageRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ConversationContextRequest(BaseModel):
    messages: list[ConversationMessageRequest] = Field(default_factory=list, max_length=20)


class AgentRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None
    continuation: AgentContinuationRequest | None = None
    conversation_context: ConversationContextRequest | None = None


class AgentContinuationResponse(BaseModel):
    kind: AgentContinuationKind
    route: ShipmentContinuationRoute
    original_identifier: str


class AgentActionResponse(BaseModel):
    id: UUID
    action_type: AgentActionType
    status: AgentActionStatus
    resource_type: str
    resource_id: UUID
    shipment_identifier: str
    summary: str
    expected_status: str
    target_status: str | None = None
    new_notes: str | None = None
    result_summary: str | None = None
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class AgentResponse(BaseModel):
    answer: str
    continuation: AgentContinuationResponse | None = None


class AgentActionMutationResponse(BaseModel):
    answer: str
    action: AgentActionResponse


class ConversationSummaryResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationMessageResponse(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageResponse]
    continuation: AgentContinuationResponse | None = None
    pending_action: AgentActionResponse | None = None


class ShipmentOperationalIssueResponse(BaseModel):
    code: str
    severity: OperationalSeverity
    message: str
    recommended_action: str
    age_seconds: int | None


class ShipmentOperationalAnalysisResponse(BaseModel):
    shipment_id: UUID
    identifier: str
    identifier_kind: ShipmentIdentifierKind
    has_issues: bool
    highest_severity: OperationalSeverity
    risk_score: int
    risk_level: OperationalRiskLevel
    issues: list[ShipmentOperationalIssueResponse]


def get_answer_question_service(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnswerQuestionService:
    return build_answer_question_service(settings=settings, session=session)


def get_agent_runtime(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LangGraphAgentRuntime:
    return build_agent_runtime(settings=settings, session=session)


def get_conversation_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConversationService:
    return build_conversation_service(session=session)


def get_agent_action_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgentActionService:
    return build_agent_action_service(session=session)


def get_resolve_shipment_service() -> ResolveShipmentService:
    return build_resolve_shipment_service()


def get_analyze_shipment_service() -> AnalyzeShipmentService:
    return build_analyze_shipment_service()


def _continuation_from_request(
    continuation: AgentContinuationRequest | None,
) -> AgentContinuation | None:
    if continuation is None:
        return None

    return AgentContinuation(
        kind=continuation.kind,
        route=continuation.route,
        original_identifier=continuation.original_identifier,
    )


def _continuation_response(
    continuation: AgentContinuation | None,
) -> AgentContinuationResponse | None:
    if continuation is None:
        return None

    return AgentContinuationResponse(
        kind=continuation.kind,
        route=continuation.route,
        original_identifier=continuation.original_identifier,
    )


def _agent_action_response(
    action: StoredAgentAction,
) -> AgentActionResponse:
    return AgentActionResponse(
        id=action.id,
        action_type=action.action_type,
        status=action.status,
        resource_type=action.resource_type,
        resource_id=action.resource_id,
        shipment_identifier=action.shipment_identifier,
        summary=action.summary,
        expected_status=action.expected_status,
        target_status=action.target_status,
        new_notes=action.new_notes,
        result_summary=action.result_summary,
        failure_reason=action.failure_reason,
        created_at=action.created_at,
        updated_at=action.updated_at,
    )


def _conversation_summary_response(
    conversation: ConversationSummary,
) -> ConversationSummaryResponse:
    return ConversationSummaryResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _conversation_detail_response(
    conversation: ConversationDetail,
    *,
    pending_action: StoredAgentAction | None = None,
) -> ConversationDetailResponse:
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            ConversationMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in conversation.messages
        ],
        continuation=_continuation_response(conversation.continuation),
        pending_action=(
            _agent_action_response(pending_action) if pending_action is not None else None
        ),
    )


@router.post("/tenants/{tenant_id}/ask", response_model=AskQuestionResponse)
async def ask_question(
    tenant_id: UUID,
    payload: AskQuestionRequest,
    service: Annotated[AnswerQuestionService, Depends(get_answer_question_service)],
    _membership: Annotated[
        Membership,
        Depends(require_entitlement(Entitlements.AI_ASSISTANT)),
    ],
) -> AskQuestionResponse:
    answer = await service.execute(
        tenant_id=tenant_id,
        question=payload.question,
        limit=payload.limit,
    )

    return AskQuestionResponse(
        content=answer.content,
        model=answer.model,
        sources=[
            RAGSourceResponse(
                chunk_id=source.chunk.id,
                document_id=source.chunk.document_id,
                chunk_index=source.chunk.chunk_index,
                content=source.chunk.content,
                score=source.score,
            )
            for source in answer.sources
        ],
    )


@router.post(
    "/tenants/{tenant_id}/conversations",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    tenant_id: UUID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    membership: Annotated[
        Membership,
        Depends(require_entitlement(Entitlements.AI_ASSISTANT)),
    ],
) -> ConversationDetailResponse:
    conversation = await service.create(
        tenant_id=tenant_id,
        user_id=membership.user_id,
    )

    return _conversation_detail_response(conversation)


@router.get(
    "/tenants/{tenant_id}/conversations",
    response_model=list[ConversationSummaryResponse],
)
async def list_conversations(
    tenant_id: UUID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    membership: Annotated[
        Membership,
        Depends(require_entitlement(Entitlements.AI_ASSISTANT)),
    ],
) -> list[ConversationSummaryResponse]:
    conversations = await service.list(
        tenant_id=tenant_id,
        user_id=membership.user_id,
    )

    return [_conversation_summary_response(item) for item in conversations]


@router.get(
    "/tenants/{tenant_id}/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    tenant_id: UUID,
    conversation_id: UUID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    action_service: Annotated[AgentActionService, Depends(get_agent_action_service)],
    membership: Annotated[
        Membership,
        Depends(require_entitlement(Entitlements.AI_ASSISTANT)),
    ],
) -> ConversationDetailResponse:
    try:
        conversation = await service.get(
            tenant_id=tenant_id,
            user_id=membership.user_id,
            conversation_id=conversation_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        ) from exc

    pending_action = await action_service.get_active_for_conversation(
        tenant_id=tenant_id,
        user_id=membership.user_id,
        conversation_id=conversation_id,
    )

    return _conversation_detail_response(
        conversation,
        pending_action=pending_action,
    )


@router.delete(
    "/tenants/{tenant_id}/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    tenant_id: UUID,
    conversation_id: UUID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    action_service: Annotated[AgentActionService, Depends(get_agent_action_service)],
    membership: Annotated[
        Membership,
        Depends(require_entitlement(Entitlements.AI_ASSISTANT)),
    ],
) -> Response:
    active_action = await action_service.get_active_for_conversation(
        tenant_id=tenant_id,
        user_id=membership.user_id,
        conversation_id=conversation_id,
    )

    if active_action is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("Confirm or cancel the pending AI action before deleting this conversation"),
        )

    try:
        await service.delete(
            tenant_id=tenant_id,
            user_id=membership.user_id,
            conversation_id=conversation_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/tenants/{tenant_id}/agent",
    response_model=AgentResponse,
)
async def run_agent(
    tenant_id: UUID,
    payload: AgentRequest,
    runtime: Annotated[LangGraphAgentRuntime, Depends(get_agent_runtime)],
    conversation_service: Annotated[
        ConversationService,
        Depends(get_conversation_service),
    ],
    action_service: Annotated[
        AgentActionService,
        Depends(get_agent_action_service),
    ],
    membership: Annotated[
        Membership,
        Depends(require_entitlement(Entitlements.AI_ASSISTANT)),
    ],
) -> AgentResponse:
    requested_continuation = _continuation_from_request(payload.continuation)
    continuation = requested_continuation
    conversation_context: ConversationContext | None = None
    persistent_conversation_id = payload.conversation_id

    try:
        if persistent_conversation_id is not None:
            active_action = await action_service.get_active_for_conversation(
                tenant_id=tenant_id,
                user_id=membership.user_id,
                conversation_id=persistent_conversation_id,
            )

            if active_action is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Confirm or cancel the pending AI action before sending another message"
                    ),
                )

            prepared_turn = await conversation_service.prepare_turn(
                tenant_id=tenant_id,
                user_id=membership.user_id,
                conversation_id=persistent_conversation_id,
                question=payload.question,
            )
            conversation_context = prepared_turn.conversation_context

            if "continuation" in payload.model_fields_set:
                if (
                    requested_continuation is not None
                    and requested_continuation != prepared_turn.continuation
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Continuation does not match conversation state",
                    )
            else:
                continuation = prepared_turn.continuation
        elif payload.conversation_context is not None:
            conversation_context = ConversationContext(
                messages=tuple(
                    ConversationMessage(
                        role=message.role,
                        content=message.content,
                    )
                    for message in payload.conversation_context.messages
                )
            )

        result = await runtime.execute_with_context(
            tenant_id=tenant_id,
            role_id=membership.role_id,
            question=payload.question,
            continuation=continuation,
            conversation_context=conversation_context,
        )

        if result.action_proposal is not None:
            if persistent_conversation_id is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "AI write actions require a persistent conversation "
                        "so confirmation can be recorded safely"
                    ),
                )

            await action_service.propose(
                tenant_id=tenant_id,
                user_id=membership.user_id,
                conversation_id=persistent_conversation_id,
                proposal=result.action_proposal,
            )

        if persistent_conversation_id is not None:
            await conversation_service.complete_turn(
                tenant_id=tenant_id,
                user_id=membership.user_id,
                conversation_id=persistent_conversation_id,
                answer=result.answer,
                continuation=result.continuation,
            )
    except PendingAgentActionExistsError as exc:
        await conversation_service.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation already has a pending AI action",
        ) from exc
    except ConversationNotFoundError as exc:
        await conversation_service.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        ) from exc
    except Exception:
        if persistent_conversation_id is not None:
            await conversation_service.rollback()
        raise

    return AgentResponse(
        answer=result.answer,
        continuation=_continuation_response(result.continuation),
    )


@router.post(
    "/tenants/{tenant_id}/actions/{action_id}/confirm",
    response_model=AgentActionMutationResponse,
)
async def confirm_agent_action(
    tenant_id: UUID,
    action_id: UUID,
    action_service: Annotated[AgentActionService, Depends(get_agent_action_service)],
    conversation_service: Annotated[
        ConversationService,
        Depends(get_conversation_service),
    ],
    membership: Annotated[
        Membership,
        Depends(require_entitlement(Entitlements.AI_ASSISTANT)),
    ],
) -> AgentActionMutationResponse:
    try:
        mutation = await action_service.confirm(
            tenant_id=tenant_id,
            user_id=membership.user_id,
            role_id=membership.role_id,
            action_id=action_id,
        )
    except AgentActionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI action not found",
        ) from exc
    except AgentActionPermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied for this AI action",
        ) from exc
    except AgentActionInProgressError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI action is already being executed",
        ) from exc
    except AgentActionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc) or "AI action cannot be confirmed",
        ) from exc
    except AgentActionExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    action = mutation.action
    answer = action.result_summary or "AI action completed."

    if mutation.changed:
        await conversation_service.complete_turn(
            tenant_id=tenant_id,
            user_id=membership.user_id,
            conversation_id=action.conversation_id,
            answer=answer,
            continuation=None,
        )

    return AgentActionMutationResponse(
        answer=answer,
        action=_agent_action_response(action),
    )


@router.post(
    "/tenants/{tenant_id}/actions/{action_id}/cancel",
    response_model=AgentActionMutationResponse,
)
async def cancel_agent_action(
    tenant_id: UUID,
    action_id: UUID,
    action_service: Annotated[AgentActionService, Depends(get_agent_action_service)],
    conversation_service: Annotated[
        ConversationService,
        Depends(get_conversation_service),
    ],
    membership: Annotated[
        Membership,
        Depends(require_entitlement(Entitlements.AI_ASSISTANT)),
    ],
) -> AgentActionMutationResponse:
    try:
        mutation = await action_service.cancel(
            tenant_id=tenant_id,
            user_id=membership.user_id,
            action_id=action_id,
        )
    except AgentActionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI action not found",
        ) from exc
    except AgentActionInProgressError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI action is already being executed",
        ) from exc
    except AgentActionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc) or "AI action cannot be cancelled",
        ) from exc

    action = mutation.action
    answer = f"Cancelled pending AI action: {action.summary}"

    if mutation.changed:
        await conversation_service.complete_turn(
            tenant_id=tenant_id,
            user_id=membership.user_id,
            conversation_id=action.conversation_id,
            answer=answer,
            continuation=None,
        )

    return AgentActionMutationResponse(
        answer=answer,
        action=_agent_action_response(action),
    )


@router.get(
    "/tenants/{tenant_id}/shipments/{shipment_identifier}/operations",
    response_model=ShipmentOperationalAnalysisResponse,
)
async def analyze_shipment_operations(
    tenant_id: UUID,
    shipment_identifier: str,
    resolve_service: Annotated[
        ResolveShipmentService,
        Depends(get_resolve_shipment_service),
    ],
    analyze_service: Annotated[
        AnalyzeShipmentService,
        Depends(get_analyze_shipment_service),
    ],
    _membership: Annotated[
        Membership,
        Depends(require_entitlement(Entitlements.AI_ASSISTANT)),
    ],
    _shipment_event_access: Annotated[
        Membership,
        Depends(require_permission(Permissions.SHIPMENT_EVENT_READ)),
    ],
) -> ShipmentOperationalAnalysisResponse:
    try:
        resolved = await resolve_service.execute(
            tenant_id=tenant_id,
            identifier=shipment_identifier,
        )
    except ShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc
    except ShipmentIdentifierAmbiguousError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shipment identifier matches multiple shipments",
        ) from exc

    analysis = await analyze_service.execute(
        tenant_id=tenant_id,
        shipment_id=resolved.shipment_id,
    )

    return ShipmentOperationalAnalysisResponse(
        shipment_id=resolved.shipment_id,
        identifier=resolved.identifier,
        identifier_kind=resolved.identifier_kind,
        has_issues=analysis.has_issues,
        highest_severity=analysis.highest_severity,
        risk_score=analysis.risk_score,
        risk_level=analysis.risk_level,
        issues=[
            ShipmentOperationalIssueResponse(
                code=issue.code,
                severity=issue.severity,
                message=issue.message,
                recommended_action=issue.recommended_action,
                age_seconds=(
                    max(0, int(issue.age.total_seconds())) if issue.age is not None else None
                ),
            )
            for issue in analysis.issues
        ],
    )
