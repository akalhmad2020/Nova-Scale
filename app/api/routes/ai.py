from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

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
    build_agent_runtime,
    build_analyze_shipment_service,
    build_answer_question_service,
    build_conversation_service,
    build_resolve_shipment_service,
)
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


class AgentResponse(BaseModel):
    answer: str
    continuation: AgentContinuationResponse | None = None


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

    return _conversation_detail_response(conversation)


@router.delete(
    "/tenants/{tenant_id}/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    tenant_id: UUID,
    conversation_id: UUID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    membership: Annotated[
        Membership,
        Depends(require_entitlement(Entitlements.AI_ASSISTANT)),
    ],
) -> Response:
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

        if persistent_conversation_id is not None:
            await conversation_service.complete_turn(
                tenant_id=tenant_id,
                user_id=membership.user_id,
                conversation_id=persistent_conversation_id,
                answer=result.answer,
                continuation=result.continuation,
            )
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
