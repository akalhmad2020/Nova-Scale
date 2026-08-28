from types import TracebackType
from typing import Protocol, Self

from app.modules.carriers.infrastructure.repositories.carrier_repository import (
    CarrierRepository,
)
from app.modules.carriers.infrastructure.repositories.carrier_service_repository import (
    CarrierServiceRepository,
)
from app.modules.documents.application.ports.document_repository import (
    DocumentRepository,
)
from app.modules.documents.application.ports.shipment_label_repository import (
    ShipmentLabelRepository,
)
from app.modules.documents.infrastructure.models import Document, ShipmentLabel
from app.modules.packages.infrastructure.repositories.package_repository import (
    PackageRepository,
)
from app.modules.shipments.infrastructure.repositories.shipment_repository import (
    ShipmentRepository,
)


class DocumentsUnitOfWork(Protocol):
    documents: DocumentRepository
    shipment_labels: ShipmentLabelRepository
    shipments: ShipmentRepository
    packages: PackageRepository
    carriers: CarrierRepository
    carrier_services: CarrierServiceRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def flush(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def refresh(
        self,
        instance: Document | ShipmentLabel,
    ) -> None: ...
