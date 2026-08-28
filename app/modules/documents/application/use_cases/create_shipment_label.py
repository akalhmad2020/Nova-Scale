from dataclasses import dataclass
from uuid import UUID

from app.modules.documents.application.exceptions import (
    CarrierNotFoundError,
    CarrierServiceMismatchError,
    CarrierServiceNotFoundError,
    PackageNotFoundError,
    PackageShipmentMismatchError,
    ShipmentNotFoundError,
)
from app.modules.documents.application.ports.unit_of_work import (
    DocumentsUnitOfWork,
)
from app.modules.documents.domain.enums import LabelStatus
from app.modules.documents.infrastructure.models.shipment_label import ShipmentLabel


@dataclass(frozen=True, slots=True)
class CreateShipmentLabelCommand:
    tenant_id: UUID
    shipment_id: UUID
    package_id: UUID | None = None
    carrier_id: UUID | None = None
    carrier_service_id: UUID | None = None


class CreateShipmentLabelUseCase:
    def __init__(
        self,
        unit_of_work: DocumentsUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateShipmentLabelCommand,
    ) -> ShipmentLabel:
        async with self._unit_of_work:
            shipment = await self._unit_of_work.shipments.get_by_id_and_tenant(
                command.shipment_id,
                command.tenant_id,
            )

            if shipment is None:
                raise ShipmentNotFoundError

            if command.package_id is not None:
                package = await self._unit_of_work.packages.get_by_id_and_tenant(
                    command.package_id,
                    command.tenant_id,
                )

                if package is None:
                    raise PackageNotFoundError

                if package.shipment_id != command.shipment_id:
                    raise PackageShipmentMismatchError

            if command.carrier_id is not None:
                carrier = await self._unit_of_work.carriers.get_by_id_and_tenant(
                    command.carrier_id,
                    command.tenant_id,
                )

                if carrier is None:
                    raise CarrierNotFoundError

            if command.carrier_service_id is not None:
                carrier_service = await self._unit_of_work.carrier_services.get_by_id_and_tenant(
                    command.carrier_service_id,
                    command.tenant_id,
                )

                if carrier_service is None:
                    raise CarrierServiceNotFoundError

                if (
                    command.carrier_id is not None
                    and carrier_service.carrier_id != command.carrier_id
                ):
                    raise CarrierServiceMismatchError

            shipment_label = ShipmentLabel(
                tenant_id=command.tenant_id,
                shipment_id=command.shipment_id,
                package_id=command.package_id,
                carrier_id=command.carrier_id,
                carrier_service_id=command.carrier_service_id,
                status=LabelStatus.PENDING,
                tracking_number=None,
                document_id=None,
            )

            self._unit_of_work.shipment_labels.add(shipment_label)

            await self._unit_of_work.flush()
            await self._unit_of_work.refresh(shipment_label)
            await self._unit_of_work.commit()

            return shipment_label
