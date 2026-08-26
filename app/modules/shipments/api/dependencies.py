from app.core.database import SessionFactory
from app.modules.shipments.application.use_cases.create_shipment import (
    CreateShipment,
)
from app.modules.shipments.application.use_cases.delete_shipment import (
    DeleteShipment,
)
from app.modules.shipments.application.use_cases.get_shipment import (
    GetShipment,
)
from app.modules.shipments.application.use_cases.list_shipments import (
    ListShipments,
)
from app.modules.shipments.application.use_cases.transition_shipment_status import (
    TransitionShipmentStatus,
)
from app.modules.shipments.application.use_cases.update_shipment import (
    UpdateShipment,
)
from app.modules.shipments.infrastructure.unit_of_work import SQLAlchemyUnitOfWork


def get_create_shipment_use_case() -> CreateShipment:
    return CreateShipment(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_get_shipment_use_case() -> GetShipment:
    return GetShipment(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_shipments_use_case() -> ListShipments:
    return ListShipments(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_update_shipment_use_case() -> UpdateShipment:
    return UpdateShipment(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_delete_shipment_use_case() -> DeleteShipment:
    return DeleteShipment(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_transition_shipment_status_use_case() -> TransitionShipmentStatus:
    return TransitionShipmentStatus(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )
