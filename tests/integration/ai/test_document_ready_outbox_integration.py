from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.application.services.retrieve_context import RetrieveContextService
from app.ai.infrastructure.dependencies import build_embedding_provider
from app.ai.infrastructure.vector_store.models import RagChunkModel
from app.ai.infrastructure.vector_store.postgres_vector_store import (
    PostgresVectorStore,
)
from app.core.config import get_settings
from app.modules.customers.domain.enums import CustomerStatus
from app.modules.customers.infrastructure.models.customer import Customer
from app.modules.documents.application.events import DOCUMENT_READY_EVENT_TYPE
from app.modules.documents.domain.enums import (
    DocumentStatus,
    DocumentType,
)
from app.modules.documents.infrastructure.models.document import Document
from app.modules.identity.domain.enums import TenantStatus
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location
from app.modules.shipments.domain.enums import (
    ServiceType,
    ShipmentStatus,
    WeightUnit,
)
from app.modules.shipments.infrastructure.models.shipment import Shipment
from app.shared.outbox.domain.enums import OutboxMessageStatus
from app.shared.outbox.infrastructure.models.outbox_message import OutboxMessage
from app.shared.outbox.infrastructure.runtime import (
    build_outbox_processing_service,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.external_ai,
]


async def create_ready_document_and_outbox_message(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    storage_key: str,
) -> tuple[UUID, UUID, UUID]:
    async with session_factory() as session:
        unique = uuid4()

        tenant = Tenant(
            name="AI Outbox Integration Tenant",
            slug=f"ai-outbox-{unique}",
            status=TenantStatus.ACTIVE,
        )

        session.add(tenant)
        await session.flush()

        customer = Customer(
            tenant_id=tenant.id,
            name="AI Outbox Customer",
            code=f"AI-CUSTOMER-{unique}",
            status=CustomerStatus.ACTIVE,
        )

        origin_location = Location(
            tenant_id=tenant.id,
            name="AI Outbox Origin",
            code=f"AI-ORIGIN-{unique}",
            type=LocationType.WAREHOUSE,
            country_code="PS",
            city="Ramallah",
            address_line1="Origin Industrial Zone",
            status=LocationStatus.ACTIVE,
        )

        destination_location = Location(
            tenant_id=tenant.id,
            name="AI Outbox Destination",
            code=f"AI-DESTINATION-{unique}",
            type=LocationType.WAREHOUSE,
            country_code="PS",
            city="Ramallah",
            address_line1="Destination Industrial Zone",
            status=LocationStatus.ACTIVE,
        )

        session.add_all(
            [
                customer,
                origin_location,
                destination_location,
            ]
        )
        await session.flush()

        shipment = Shipment(
            tenant_id=tenant.id,
            customer_id=customer.id,
            origin_location_id=origin_location.id,
            destination_location_id=destination_location.id,
            tracking_number=f"NOVA-OUTBOX-{unique}",
            reference="AI-OUTBOX-REF",
            status=ShipmentStatus.DRAFT,
            service_type=ServiceType.STANDARD,
            description="AI document ready outbox integration shipment",
            weight=Decimal("5.000"),
            weight_unit=WeightUnit.KG,
            notes="AI outbox integration test",
        )

        session.add(shipment)
        await session.flush()

        document = Document(
            tenant_id=tenant.id,
            shipment_id=shipment.id,
            type=DocumentType.OTHER,
            status=DocumentStatus.READY,
            filename="customs-status.txt",
            content_type="text/plain",
            storage_key=storage_key,
        )

        session.add(document)
        await session.flush()

        message = OutboxMessage(
            tenant_id=tenant.id,
            event_type=DOCUMENT_READY_EVENT_TYPE,
            payload={
                "document_id": str(document.id),
            },
        )

        session.add(message)
        await session.commit()

        return tenant.id, document.id, message.id


async def test_document_ready_outbox_indexes_stored_document(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    storage_root = tmp_path / "storage"
    document_directory = storage_root / "documents"

    document_directory.mkdir(
        parents=True,
    )

    storage_key = "documents/customs-status.txt"

    document_path = storage_root / storage_key
    document_path.write_text(
        ("Shipment NOVA-OUTBOX-200 is currently waiting for customs clearance."),
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "AI_DOCUMENT_STORAGE_ROOT",
        str(storage_root),
    )

    get_settings.cache_clear()
    settings = get_settings()

    try:
        tenant_id, document_id, message_id = await create_ready_document_and_outbox_message(
            session_factory,
            storage_key=storage_key,
        )

        service = build_outbox_processing_service(
            session_factory=session_factory,
            settings=settings,
        )

        now = datetime.now(UTC)

        processed_count = await service.process_batch(
            now=now,
        )

        assert processed_count == 1

        async with session_factory() as session:
            message = await session.get(
                OutboxMessage,
                message_id,
            )

            assert message is not None
            assert message.status == OutboxMessageStatus.PROCESSED
            assert message.processed_at == now
            assert message.attempt_count == 1
            assert message.claim_token is None
            assert message.lease_expires_at is None
            assert message.last_error is None

            result = await session.execute(
                select(RagChunkModel)
                .where(
                    RagChunkModel.tenant_id == tenant_id,
                    RagChunkModel.document_id == str(document_id),
                )
                .order_by(RagChunkModel.chunk_index)
            )

            stored_chunks = tuple(result.scalars().all())

            assert stored_chunks
            assert any("customs clearance" in chunk.content for chunk in stored_chunks)

        embedding_provider = build_embedding_provider(settings)

        async with session_factory() as session:
            vector_store = PostgresVectorStore(
                session=session,
            )

            retrieve_context_service = RetrieveContextService(
                embedding_provider=embedding_provider,
                vector_store=vector_store,
            )

            retrieved_chunks = await retrieve_context_service.execute(
                tenant_id=tenant_id,
                query="What is the customs status of the shipment?",
                limit=5,
            )

            assert retrieved_chunks
            assert retrieved_chunks[0].chunk.document_id == str(document_id)
            assert "customs clearance" in (retrieved_chunks[0].chunk.content)

    finally:
        get_settings.cache_clear()
