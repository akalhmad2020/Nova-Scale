from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.documents.domain.enums import DocumentStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)


class DocumentReadyDocumentNotFoundError(Exception):
    pass


class DocumentReadyDocumentNotReadyError(Exception):
    pass


class InvalidDocumentReadyOutboxPayloadError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ReadyDocument:
    id: UUID
    status: DocumentStatus
    storage_key: str
    content_type: str


class DocumentReadyDocumentResolver(Protocol):
    async def get_document(
        self,
        *,
        tenant_id: UUID,
        document_id: UUID,
    ) -> ReadyDocument | None: ...


class IndexReadyDocument(Protocol):
    async def execute(
        self,
        *,
        tenant_id: UUID,
        document: ReadyDocument,
    ) -> int: ...


class DocumentReadyOutboxHandler:
    def __init__(
        self,
        *,
        document_resolver: DocumentReadyDocumentResolver,
        index_document: IndexReadyDocument,
    ) -> None:
        self._document_resolver = document_resolver
        self._index_document = index_document

    async def handle(
        self,
        message: OutboxMessage,
    ) -> None:
        document_id = self._require_uuid(
            payload=message.payload,
            field="document_id",
        )

        document = await self._document_resolver.get_document(
            tenant_id=message.tenant_id,
            document_id=document_id,
        )

        if document is None:
            raise DocumentReadyDocumentNotFoundError(
                "Document referenced by document.ready was not found."
            )

        if document.status != DocumentStatus.READY:
            raise DocumentReadyDocumentNotReadyError(
                "Document referenced by document.ready is not ready."
            )

        await self._index_document.execute(
            tenant_id=message.tenant_id,
            document=document,
        )

    def _require_string(
        self,
        *,
        payload: dict[str, object],
        field: str,
    ) -> str:
        value = payload.get(field)

        if not isinstance(value, str):
            raise InvalidDocumentReadyOutboxPayloadError(
                f"Document ready outbox payload field '{field}' must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise InvalidDocumentReadyOutboxPayloadError(
                f"Document ready outbox payload field '{field}' cannot be empty."
            )

        return normalized

    def _require_uuid(
        self,
        *,
        payload: dict[str, object],
        field: str,
    ) -> UUID:
        value = self._require_string(
            payload=payload,
            field=field,
        )

        try:
            return UUID(value)
        except ValueError as exc:
            raise InvalidDocumentReadyOutboxPayloadError(
                f"Document ready outbox payload field '{field}' must be a valid UUID."
            ) from exc
