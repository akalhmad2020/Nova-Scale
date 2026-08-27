from dataclasses import dataclass
from uuid import UUID

from app.modules.packages.application.exceptions import (
    PackageShipmentNotFoundError,
)
from app.modules.packages.application.ports.unit_of_work import UnitOfWork
from app.modules.packages.infrastructure.models.package import Package


@dataclass(frozen=True, slots=True)
class ListPackagesQuery:
    tenant_id: UUID
    shipment_id: UUID


class ListPackages:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: ListPackagesQuery,
    ) -> list[Package]:
        async with self._unit_of_work as uow:
            shipment = await uow.shipments.get_by_id_and_tenant(
                query.shipment_id,
                query.tenant_id,
            )

            if shipment is None:
                raise PackageShipmentNotFoundError

            return await uow.packages.list_by_shipment(
                query.shipment_id,
                query.tenant_id,
            )
