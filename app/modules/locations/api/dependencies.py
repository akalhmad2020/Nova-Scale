from app.core.database import SessionFactory
from app.modules.locations.application.use_cases.create_location import (
    CreateLocation,
)
from app.modules.locations.application.use_cases.delete_location import (
    DeleteLocation,
)
from app.modules.locations.application.use_cases.get_location import (
    GetLocation,
)
from app.modules.locations.application.use_cases.list_locations import (
    ListLocations,
)
from app.modules.locations.application.use_cases.update_location import (
    UpdateLocation,
)
from app.modules.locations.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


def get_create_location_use_case() -> CreateLocation:
    return CreateLocation(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_get_location_use_case() -> GetLocation:
    return GetLocation(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_locations_use_case() -> ListLocations:
    return ListLocations(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_update_location_use_case() -> UpdateLocation:
    return UpdateLocation(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_delete_location_use_case() -> DeleteLocation:
    return DeleteLocation(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )
