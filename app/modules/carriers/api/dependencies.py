from app.core.database import SessionFactory
from app.modules.carriers.application.use_cases.create_carrier import (
    CreateCarrier,
)
from app.modules.carriers.application.use_cases.create_carrier_service import (
    CreateCarrierService,
)
from app.modules.carriers.application.use_cases.deactivate_carrier import (
    DeactivateCarrier,
)
from app.modules.carriers.application.use_cases.deactivate_carrier_service import (
    DeactivateCarrierService,
)
from app.modules.carriers.application.use_cases.get_carrier import (
    GetCarrier,
)
from app.modules.carriers.application.use_cases.get_carrier_service import (
    GetCarrierService,
)
from app.modules.carriers.application.use_cases.list_carrier_services import (
    ListCarrierServices,
)
from app.modules.carriers.application.use_cases.list_carriers import (
    ListCarriers,
)
from app.modules.carriers.application.use_cases.update_carrier import (
    UpdateCarrier,
)
from app.modules.carriers.application.use_cases.update_carrier_service import (
    UpdateCarrierService,
)
from app.modules.carriers.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


def get_create_carrier_use_case() -> CreateCarrier:
    return CreateCarrier(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_get_carrier_use_case() -> GetCarrier:
    return GetCarrier(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_carriers_use_case() -> ListCarriers:
    return ListCarriers(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_update_carrier_use_case() -> UpdateCarrier:
    return UpdateCarrier(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_deactivate_carrier_use_case() -> DeactivateCarrier:
    return DeactivateCarrier(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_create_carrier_service_use_case() -> CreateCarrierService:
    return CreateCarrierService(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_get_carrier_service_use_case() -> GetCarrierService:
    return GetCarrierService(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_carrier_services_use_case() -> ListCarrierServices:
    return ListCarrierServices(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_update_carrier_service_use_case() -> UpdateCarrierService:
    return UpdateCarrierService(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_deactivate_carrier_service_use_case() -> DeactivateCarrierService:
    return DeactivateCarrierService(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )
