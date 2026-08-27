from app.core.database import SessionFactory
from app.modules.packages.application.use_cases.create_package import (
    CreatePackage,
)
from app.modules.packages.application.use_cases.delete_package import (
    DeletePackage,
)
from app.modules.packages.application.use_cases.get_package import (
    GetPackage,
)
from app.modules.packages.application.use_cases.list_packages import (
    ListPackages,
)
from app.modules.packages.application.use_cases.update_package import (
    UpdatePackage,
)
from app.modules.packages.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


def get_create_package_use_case() -> CreatePackage:
    return CreatePackage(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_get_package_use_case() -> GetPackage:
    return GetPackage(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_packages_use_case() -> ListPackages:
    return ListPackages(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_update_package_use_case() -> UpdatePackage:
    return UpdatePackage(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_delete_package_use_case() -> DeletePackage:
    return DeletePackage(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )
