from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.packages.application.exceptions import (
    PackageNotFoundError,
    PackageNumberAlreadyExistsError,
    PackageShipmentNotFoundError,
)
from app.modules.packages.application.ports.unit_of_work import UnitOfWork
from app.modules.packages.domain.enums import DimensionUnit
from app.modules.packages.infrastructure.models.package import Package
from app.modules.shipments.domain.enums import WeightUnit


@dataclass(frozen=True, slots=True)
class UpdatePackageCommand:
    tenant_id: UUID
    package_id: UUID
    shipment_id: UUID
    package_number: str
    weight: Decimal
    weight_unit: WeightUnit
    description: str | None = None
    length: Decimal | None = None
    width: Decimal | None = None
    height: Decimal | None = None
    dimension_unit: DimensionUnit | None = None
    notes: str | None = None


class UpdatePackage:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: UpdatePackageCommand,
    ) -> Package:
        package_number = command.package_number.strip().upper()

        description = command.description.strip() if command.description is not None else None

        notes = command.notes.strip() if command.notes is not None else None

        async with self._unit_of_work as uow:
            package = await uow.packages.get_by_id_and_tenant(
                command.package_id,
                command.tenant_id,
            )

            if package is None:
                raise PackageNotFoundError

            shipment = await uow.shipments.get_by_id_and_tenant(
                command.shipment_id,
                command.tenant_id,
            )

            if shipment is None:
                raise PackageShipmentNotFoundError

            existing = await uow.packages.get_by_number_and_shipment(
                package_number,
                command.shipment_id,
            )

            if existing is not None and existing.id != package.id:
                raise PackageNumberAlreadyExistsError

            package.shipment_id = command.shipment_id
            package.package_number = package_number
            package.description = description
            package.weight = command.weight
            package.weight_unit = command.weight_unit
            package.length = command.length
            package.width = command.width
            package.height = command.height
            package.dimension_unit = command.dimension_unit
            package.notes = notes

            await uow.flush()
            await uow.commit()
            await uow.refresh(package)

            return package
