from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.agent.shipment_operational_models import (
    OperationalRiskLevel,
    OperationalSeverity,
)
from app.ai.application.agent.shipment_resolution_exceptions import (
    ShipmentIdentifierAmbiguousError,
)
from app.ai.application.agent.shipment_resolution_models import (
    ShipmentIdentifierKind,
)
from app.ai.application.dependencies import (
    build_agent_runtime,
    build_analyze_shipment_service,
    build_answer_question_service,
    build_resolve_shipment_service,
)
from app.ai.application.services.analyze_shipment import (
    AnalyzeShipmentService,
)
from app.ai.application.services.answer_question import AnswerQuestionService
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

router = APIRouter(
    prefix="/ai",
    tags=["ai"],
)


class AskQuestionRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
    )


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


class AgentRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
    )


class AgentResponse(BaseModel):
    answer: str


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
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> AnswerQuestionService:
    return build_answer_question_service(
        settings=settings,
        session=session,
    )


def get_agent_runtime(
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> LangGraphAgentRuntime:
    return build_agent_runtime(
        settings=settings,
        session=session,
    )


def get_resolve_shipment_service() -> ResolveShipmentService:
    return build_resolve_shipment_service()


def get_analyze_shipment_service() -> AnalyzeShipmentService:
    return build_analyze_shipment_service()


@router.post(
    "/tenants/{tenant_id}/ask",
    response_model=AskQuestionResponse,
)
async def ask_question(
    tenant_id: UUID,
    payload: AskQuestionRequest,
    service: Annotated[
        AnswerQuestionService,
        Depends(get_answer_question_service),
    ],
    _membership: Annotated[
        Membership,
        Depends(require_entitlement(Entitlements.AI_ASSISTANT)),
    ],
    _document_access: Annotated[
        Membership,
        Depends(require_permission(Permissions.DOCUMENT_READ)),
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
    "/tenants/{tenant_id}/agent",
    response_model=AgentResponse,
)
async def run_agent(
    tenant_id: UUID,
    payload: AgentRequest,
    runtime: Annotated[
        LangGraphAgentRuntime,
        Depends(get_agent_runtime),
    ],
    _membership: Annotated[
        Membership,
        Depends(require_entitlement(Entitlements.AI_ASSISTANT)),
    ],
    _shipment_access: Annotated[
        Membership,
        Depends(require_permission(Permissions.SHIPMENT_READ)),
    ],
    _document_access: Annotated[
        Membership,
        Depends(require_permission(Permissions.DOCUMENT_READ)),
    ],
) -> AgentResponse:
    answer = await runtime.execute(
        tenant_id=tenant_id,
        question=payload.question,
    )

    return AgentResponse(
        answer=answer,
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
    _shipment_access: Annotated[
        Membership,
        Depends(require_permission(Permissions.SHIPMENT_READ)),
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
