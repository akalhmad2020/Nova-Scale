from uuid import UUID, uuid4

import pytest

from app.ai.infrastructure.outbox.document_ready_handler import (
    DocumentReadyDocumentNotFoundError,
    DocumentReadyDocumentNotReadyError,
    DocumentReadyOutboxHandler,
    InvalidDocumentReadyOutboxPayloadError,
    ReadyDocument,
)
from app.modules.documents.domain.enums import DocumentStatus
from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import (
    OutboxMessage,
)


class FakeDocumentResolver:
    def __init__(
        self,
        document: ReadyDocument | None,
    ) -> None:
        self._document = document
        self.calls: list[tuple[object, object]] = []

    async def get_document(
        self,
        *,
        tenant_id: UUID,
        document_id: UUID,
    ) -> ReadyDocument | None:
        self.calls.append((tenant_id, document_id))
        return self._document


class FakeIndexReadyDocument:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ReadyDocument]] = []

    async def execute(
        self,
        *,
        tenant_id: UUID,
        document: ReadyDocument,
    ) -> int:
        self.calls.append((tenant_id, document))
        return 3


def build_message(
    *,
    document_id: object,
) -> OutboxMessage:
    return OutboxMessage(
        tenant_id=uuid4(),
        event_type="document.ready",
        payload={
            "document_id": document_id,
        },
        status=OutboxMessageStatus.PENDING.value,
        attempt_count=0,
        available_at=None,
        claim_token=None,
        lease_expires_at=None,
        processed_at=None,
        last_error=None,
    )


@pytest.mark.asyncio
async def test_document_ready_handler_indexes_ready_document() -> None:
    document = ReadyDocument(
        id=uuid4(),
        status=DocumentStatus.READY,
        storage_key="documents/example.txt",
        content_type="text/plain",
    )
    resolver = FakeDocumentResolver(document)
    indexer = FakeIndexReadyDocument()

    handler = DocumentReadyOutboxHandler(
        document_resolver=resolver,
        index_document=indexer,
    )

    message = build_message(
        document_id=str(document.id),
    )

    await handler.handle(message)

    assert resolver.calls == [
        (
            message.tenant_id,
            document.id,
        )
    ]
    assert indexer.calls == [
        (
            message.tenant_id,
            document,
        )
    ]


@pytest.mark.asyncio
async def test_document_ready_handler_rejects_missing_document() -> None:
    document_id = uuid4()
    resolver = FakeDocumentResolver(None)
    indexer = FakeIndexReadyDocument()

    handler = DocumentReadyOutboxHandler(
        document_resolver=resolver,
        index_document=indexer,
    )

    message = build_message(
        document_id=str(document_id),
    )

    with pytest.raises(DocumentReadyDocumentNotFoundError):
        await handler.handle(message)

    assert indexer.calls == []


@pytest.mark.asyncio
async def test_document_ready_handler_rejects_document_not_ready() -> None:
    document = ReadyDocument(
        id=uuid4(),
        status=DocumentStatus.PENDING,
        storage_key="documents/example.txt",
        content_type="text/plain",
    )
    resolver = FakeDocumentResolver(document)
    indexer = FakeIndexReadyDocument()

    handler = DocumentReadyOutboxHandler(
        document_resolver=resolver,
        index_document=indexer,
    )

    message = build_message(
        document_id=str(document.id),
    )

    with pytest.raises(DocumentReadyDocumentNotReadyError):
        await handler.handle(message)

    assert indexer.calls == []


@pytest.mark.asyncio
async def test_document_ready_handler_rejects_invalid_document_id() -> None:
    resolver = FakeDocumentResolver(None)
    indexer = FakeIndexReadyDocument()

    handler = DocumentReadyOutboxHandler(
        document_resolver=resolver,
        index_document=indexer,
    )

    message = build_message(
        document_id="not-a-uuid",
    )

    with pytest.raises(InvalidDocumentReadyOutboxPayloadError):
        await handler.handle(message)

    assert resolver.calls == []
    assert indexer.calls == []


@pytest.mark.asyncio
async def test_document_ready_handler_rejects_missing_document_id() -> None:
    resolver = FakeDocumentResolver(None)
    indexer = FakeIndexReadyDocument()

    handler = DocumentReadyOutboxHandler(
        document_resolver=resolver,
        index_document=indexer,
    )

    message = build_message(
        document_id=None,
    )

    with pytest.raises(InvalidDocumentReadyOutboxPayloadError):
        await handler.handle(message)

    assert resolver.calls == []
    assert indexer.calls == []
