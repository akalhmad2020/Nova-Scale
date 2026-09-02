from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.ai.infrastructure.outbox.adapters import (
    IndexReadyDocumentAdapter,
    SQLAlchemyDocumentReadyDocumentResolverAdapter,
)
from app.ai.infrastructure.outbox.document_ready_handler import (
    DocumentReadyOutboxHandler,
)
from app.core.config import Settings
from app.modules.documents.application.events import (
    DOCUMENT_READY_EVENT_TYPE,
)
from app.shared.outbox.infrastructure.handlers.registry import (
    OutboxMessageHandlerRegistry,
)


def register_ai_outbox_handlers(
    *,
    registry: OutboxMessageHandlerRegistry,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    document_resolver = SQLAlchemyDocumentReadyDocumentResolverAdapter(
        session_factory,
    )

    index_document = IndexReadyDocumentAdapter(
        session_factory=session_factory,
        settings=settings,
    )

    document_ready_handler = DocumentReadyOutboxHandler(
        document_resolver=document_resolver,
        index_document=index_document,
    )

    registry.register(
        DOCUMENT_READY_EVENT_TYPE,
        document_ready_handler,
    )
