from dataclasses import dataclass
from uuid import UUID

from app.modules.packages.application.exceptions import PackageNotFoundError
from app.modules.packages.application.ports.unit_of_work import UnitOfWork
from app.modules.packages.infrastructure.models.package import Package


@dataclass(frozen=True, slots=True)
class GetPackageQuery:
    tenant_id: UUID
    package_id: UUID


class GetPackage:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetPackageQuery,
    ) -> Package:
        async with self._unit_of_work as uow:
            package = await uow.packages.get_by_id_and_tenant(
                query.package_id,
                query.tenant_id,
            )

            if package is None:
                raise PackageNotFoundError

            return package
