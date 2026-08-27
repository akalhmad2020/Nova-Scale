from app.core.database import SessionFactory
from app.modules.shipment_events.application.use_cases.list_shipment_events import (
    ListShipmentEvents,
)
from app.modules.shipment_events.application.use_cases.record_shipment_event import (
    RecordShipmentEvent,
)
from app.modules.shipment_events.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


def get_record_shipment_event_use_case() -> RecordShipmentEvent:
    return RecordShipmentEvent(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_shipment_events_use_case() -> ListShipmentEvents:
    return ListShipmentEvents(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )
