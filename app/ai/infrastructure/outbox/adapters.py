from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.application.dependencies import (
    build_index_stored_document_service,
)
from app.ai.infrastructure.outbox.document_ready_handler import (
    ReadyDocument,
)
from app.core.config import Settings
from app.modules.documents.infrastructure.repositories.document_repository import (
    DocumentRepository,
)


class SQLAlchemyDocumentReadyDocumentResolverAdapter:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get_document(
        self,
        *,
        tenant_id: UUID,
        document_id: UUID,
    ) -> ReadyDocument | None:
        async with self._session_factory() as session:
            repository = DocumentRepository(session)

            document = await repository.get_by_id_and_tenant(
                document_id,
                tenant_id,
            )

            if document is None:
                return None

            return ReadyDocument(
                id=document.id,
                status=document.status,
                storage_key=document.storage_key,
                content_type=document.content_type,
            )


class IndexReadyDocumentAdapter:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings

    async def execute(
        self,
        *,
        tenant_id: UUID,
        document: ReadyDocument,
    ) -> int:
        async with self._session_factory() as session:
            service = build_index_stored_document_service(
                settings=self._settings,
                session=session,
            )

            indexed_chunks = await service.execute(
                tenant_id=tenant_id,
                document_id=document.id,
                storage_key=document.storage_key,
                content_type=document.content_type,
            )

            await session.commit()

            return indexed_chunks
