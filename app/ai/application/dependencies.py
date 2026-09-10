from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.agent.authorization import (
    AgentAuthorizationService,
)
from app.ai.application.agent.get_shipment_tool import GetShipmentTool
from app.ai.application.agent.retrieve_context_tool import RetrieveContextTool
from app.ai.application.agent.shipment_summary_tool import ShipmentSummaryTool
from app.ai.application.services.analyze_shipment import (
    AnalyzeShipmentService,
)
from app.ai.application.services.analyze_shipment_operations import (
    AnalyzeShipmentOperationsService,
)
from app.ai.application.services.answer_question import AnswerQuestionService
from app.ai.application.services.chunk_text import ChunkTextService
from app.ai.application.services.embed_document import EmbedDocumentService
from app.ai.application.services.generate_text import GenerateTextService
from app.ai.application.services.index_stored_document import (
    IndexStoredDocumentService,
)
from app.ai.application.services.ingest_document import IngestDocumentService
from app.ai.application.services.resolve_shipment import ResolveShipmentService
from app.ai.application.services.retrieve_context import RetrieveContextService
from app.ai.application.services.summarize_shipment import (
    SummarizeShipmentService,
)
from app.ai.infrastructure.agent.identity_permission_checker import (
    IdentityPermissionChecker,
)
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
from app.core.database import SessionFactory
from app.modules.identity.api.dependencies import (
    get_check_permission_use_case,
)
from app.modules.shipment_events.api.dependencies import (
    get_list_shipment_events_use_case,
)
from app.modules.shipments.api.dependencies import (
    get_get_shipment_use_case,
)
from app.modules.shipments.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork as ShipmentUnitOfWork,
)


def build_generate_text_service(
    settings: Settings,
) -> GenerateTextService:
    provider = build_llm_provider(settings)

    return GenerateTextService(
        provider=provider,
    )


def build_analyze_shipment_service() -> AnalyzeShipmentService:
    shipment_summary_tool = ShipmentSummaryTool(
        get_shipment=get_get_shipment_use_case(),
        list_shipment_events=get_list_shipment_events_use_case(),
    )

    return AnalyzeShipmentService(
        shipment_summary_tool=shipment_summary_tool,
        analyze_operations_service=AnalyzeShipmentOperationsService(),
    )


def build_resolve_shipment_service() -> ResolveShipmentService:
    return ResolveShipmentService(
        unit_of_work=ShipmentUnitOfWork(
            SessionFactory,
        ),
    )


def build_summarize_shipment_service(
    settings: Settings,
) -> SummarizeShipmentService:
    shipment_summary_tool = ShipmentSummaryTool(
        get_shipment=get_get_shipment_use_case(),
        list_shipment_events=get_list_shipment_events_use_case(),
    )

    return SummarizeShipmentService(
        shipment_summary_tool=shipment_summary_tool,
        generate_text_service=build_generate_text_service(settings),
    )


def build_retrieve_context_service(
    *,
    settings: Settings,
    session: AsyncSession,
) -> RetrieveContextService:
    embedding_provider = build_embedding_provider(settings)

    vector_store = PostgresVectorStore(
        session=session,
    )

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
    analyze_shipment_service = build_analyze_shipment_service()
    agent_planner = LLMAgentPlanner(
        generate_text_service=generate_text_service,
    )

    authorization_service = AgentAuthorizationService(
        permission_checker=IdentityPermissionChecker(
            check_permission=get_check_permission_use_case(),
        ),
    )

    resolve_shipment_service = build_resolve_shipment_service()

    summarize_shipment_service = build_summarize_shipment_service(settings)

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
        resolve_shipment_service=resolve_shipment_service,
        get_shipment_tool=get_shipment_tool,
        summarize_shipment_service=summarize_shipment_service,
        analyze_shipment_service=analyze_shipment_service,
        retrieve_context_tool=retrieve_context_tool,
        generate_text_service=generate_text_service,
        authorization_service=authorization_service,
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
