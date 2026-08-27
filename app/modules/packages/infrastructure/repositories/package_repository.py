from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.packages.infrastructure.models.package import Package


class PackageRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_by_id_and_tenant(
        self,
        package_id: UUID,
        tenant_id: UUID,
    ) -> Package | None:
        statement = select(Package).where(
            Package.id == package_id,
            Package.tenant_id == tenant_id,
            Package.deleted_at.is_(None),
        )

        package = await self._session.scalar(statement)

        return package

    async def get_by_number_and_shipment(
        self,
        package_number: str,
        shipment_id: UUID,
    ) -> Package | None:
        statement = select(Package).where(
            Package.package_number == package_number,
            Package.shipment_id == shipment_id,
            Package.deleted_at.is_(None),
        )

        package = await self._session.scalar(statement)

        return package

    async def list_by_shipment(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
    ) -> list[Package]:
        statement = (
            select(Package)
            .where(
                Package.shipment_id == shipment_id,
                Package.tenant_id == tenant_id,
                Package.deleted_at.is_(None),
            )
            .order_by(Package.created_at)
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    def add(
        self,
        package: Package,
    ) -> None:
        self._session.add(package)
