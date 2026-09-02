from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.carriers.infrastructure.repositories.carrier_repository import (
    CarrierRepository,
)
from app.modules.carriers.infrastructure.repositories.carrier_service_repository import (
    CarrierServiceRepository,
)
from app.modules.documents.application.ports.document_repository import (
    DocumentRepository as DocumentRepositoryPort,
)
from app.modules.documents.application.ports.shipment_label_repository import (
    ShipmentLabelRepository as ShipmentLabelRepositoryPort,
)
from app.modules.documents.infrastructure.models.document import Document
from app.modules.documents.infrastructure.models.shipment_label import ShipmentLabel
from app.modules.documents.infrastructure.repositories.document_repository import (
    DocumentRepository as SQLAlchemyDocumentRepository,
)
from app.modules.documents.infrastructure.repositories.shipment_label_repository import (
    ShipmentLabelRepository as SQLAlchemyShipmentLabelRepository,
)
from app.modules.packages.infrastructure.repositories.package_repository import (
    PackageRepository,
)
from app.modules.shipments.infrastructure.repositories.shipment_repository import (
    ShipmentRepository,
)
from app.shared.outbox.application.ports.repositories import (
    OutboxMessageRepository,
)
from app.shared.outbox.infrastructure.repositories.sqlalchemy import (
    SQLAlchemyOutboxMessageRepository,
)


class SQLAlchemyUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

        self.documents: DocumentRepositoryPort
        self.shipment_labels: ShipmentLabelRepositoryPort
        self.shipments: ShipmentRepository
        self.packages: PackageRepository
        self.carriers: CarrierRepository
        self.carrier_services: CarrierServiceRepository
        self.outbox_messages: OutboxMessageRepository

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self._session = self._session_factory()

        self.documents = SQLAlchemyDocumentRepository(self._session)
        self.shipment_labels = SQLAlchemyShipmentLabelRepository(self._session)
        self.shipments = ShipmentRepository(self._session)
        self.packages = PackageRepository(self._session)
        self.carriers = CarrierRepository(self._session)
        self.carrier_services = CarrierServiceRepository(self._session)
        self.outbox_messages = SQLAlchemyOutboxMessageRepository(
            self._session,
        )

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return

        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def flush(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.flush()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.rollback()

    async def refresh(
        self,
        model: Document | ShipmentLabel,
    ) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.refresh(model)
