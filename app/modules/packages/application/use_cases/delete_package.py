from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.packages.application.exceptions import PackageNotFoundError
from app.modules.packages.application.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class DeletePackageCommand:
    tenant_id: UUID
    package_id: UUID


class DeletePackage:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: DeletePackageCommand,
    ) -> None:
        async with self._unit_of_work as uow:
            package = await uow.packages.get_by_id_and_tenant(
                command.package_id,
                command.tenant_id,
            )

            if package is None:
                raise PackageNotFoundError

            package.deleted_at = datetime.now(UTC)

            await uow.flush()
            await uow.commit()
