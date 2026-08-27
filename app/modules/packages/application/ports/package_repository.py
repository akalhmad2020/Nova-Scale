from typing import Protocol
from uuid import UUID

from app.modules.packages.infrastructure.models.package import Package


class PackageRepository(Protocol):
    async def get_by_id_and_tenant(
        self,
        package_id: UUID,
        tenant_id: UUID,
    ) -> Package | None: ...

    async def get_by_number_and_shipment(
        self,
        package_number: str,
        shipment_id: UUID,
    ) -> Package | None: ...

    async def list_by_shipment(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> list[Package]: ...

    def add(
        self,
        package: Package,
    ) -> None: ...
