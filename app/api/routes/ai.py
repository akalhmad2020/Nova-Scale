from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.dependencies import (
    build_agent_runtime,
    build_answer_question_service,
)
from app.ai.application.services.answer_question import AnswerQuestionService
from app.ai.infrastructure.agent.langgraph_runtime import LangGraphAgentRuntime
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.modules.identity.api.auth_dependencies import get_current_membership
from app.modules.identity.infrastructure.models.membership import Membership

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
        Depends(get_current_membership),
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
        Depends(get_current_membership),
    ],
) -> AgentResponse:
    answer = await runtime.execute(
        tenant_id=tenant_id,
        question=payload.question,
    )

    return AgentResponse(
        answer=answer,
    )
