from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.agent.get_shipment_tool import GetShipmentTool
from app.ai.application.agent.retrieve_context_tool import (
    RetrieveContextTool,
)
from app.ai.application.services.answer_question import AnswerQuestionService
from app.ai.application.services.chunk_text import ChunkTextService
from app.ai.application.services.embed_document import EmbedDocumentService
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.application.services.index_stored_document import (
    IndexStoredDocumentService,
)
from app.ai.application.services.ingest_document import IngestDocumentService
from app.ai.application.services.retrieve_context import RetrieveContextService
from app.ai.infrastructure.agent.langgraph_runtime import (
    LangGraphAgentRuntime,
)
from app.ai.infrastructure.agent.llm_agent_planner import LLMAgentPlanner
from app.ai.infrastructure.dependencies import (
    build_embedding_provider,
    build_llm_provider,
)
from app.ai.infrastructure.document_content.local_text_reader import (
    LocalTextDocumentContentReader,
)
from app.ai.infrastructure.vector_store.postgres_vector_store import (
    PostgresVectorStore,
)
from app.core.config import Settings
from app.modules.shipments.api.dependencies import (
    get_get_shipment_use_case,
)


def build_generate_text_service(
    settings: Settings,
) -> GenerateTextService:
    provider = build_llm_provider(settings)

    return GenerateTextService(
        provider=provider,
    )


def build_retrieve_context_service(
    *,
    settings: Settings,
    session: AsyncSession,
) -> RetrieveContextService:
    embedding_provider = build_embedding_provider(settings)
    vector_store = PostgresVectorStore(session=session)

    return RetrieveContextService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )


def build_answer_question_service(
    *,
    settings: Settings,
    session: AsyncSession,
) -> AnswerQuestionService:
    retrieve_context_service = build_retrieve_context_service(
        settings=settings,
        session=session,
    )

    generate_text_service = build_generate_text_service(settings)

    return AnswerQuestionService(
        retrieve_context_service=retrieve_context_service,
        generate_text_service=generate_text_service,
    )


def build_agent_runtime(
    *,
    settings: Settings,
    session: AsyncSession,
) -> LangGraphAgentRuntime:
    generate_text_service = build_generate_text_service(settings)

    agent_planner = LLMAgentPlanner(
        generate_text_service=generate_text_service,
    )

    get_shipment_tool = GetShipmentTool(
        get_shipment=get_get_shipment_use_case(),
    )

    retrieve_context_service = build_retrieve_context_service(
        settings=settings,
        session=session,
    )

    retrieve_context_tool = RetrieveContextTool(
        retrieve_context_service=retrieve_context_service,
    )

    return LangGraphAgentRuntime(
        agent_planner=agent_planner,
        get_shipment_tool=get_shipment_tool,
        retrieve_context_tool=retrieve_context_tool,
        generate_text_service=generate_text_service,
    )


def build_index_stored_document_service(
    *,
    settings: Settings,
    session: AsyncSession,
) -> IndexStoredDocumentService:
    document_content_reader = LocalTextDocumentContentReader(
        storage_root=Path(settings.ai_document_storage_root),
    )

    embedding_provider = build_embedding_provider(settings)

    vector_store = PostgresVectorStore(
        session=session,
    )

    embed_document_service = EmbedDocumentService(
        chunk_text_service=ChunkTextService(),
        embedding_provider=embedding_provider,
    )

    ingest_document_service = IngestDocumentService(
        embed_document_service=embed_document_service,
        vector_store=vector_store,
    )

    return IndexStoredDocumentService(
        document_content_reader=document_content_reader,
        ingest_document_service=ingest_document_service,
    )
