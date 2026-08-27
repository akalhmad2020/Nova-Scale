from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.shipment_events.api.dependencies import (
    get_list_shipment_events_use_case,
    get_record_shipment_event_use_case,
)
from app.modules.shipment_events.api.schemas import (
    RecordShipmentEventRequest,
    ShipmentEventResponse,
)
from app.modules.shipment_events.application.exceptions import (
    ShipmentEventLocationNotFoundError,
    ShipmentEventShipmentNotFoundError,
)
from app.modules.shipment_events.application.use_cases.list_shipment_events import (
    ListShipmentEvents,
    ListShipmentEventsQuery,
)
from app.modules.shipment_events.application.use_cases.record_shipment_event import (
    RecordShipmentEvent,
    RecordShipmentEventCommand,
)

router = APIRouter(
    prefix="/tenants/{tenant_id}/shipments/{shipment_id}/events",
    tags=["shipment-events"],
)


@router.post(
    "",
    response_model=ShipmentEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_shipment_event(
    tenant_id: UUID,
    shipment_id: UUID,
    request: RecordShipmentEventRequest,
    membership: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.SHIPMENT_EVENT_CREATE,
            )
        ),
    ],
    use_case: Annotated[
        RecordShipmentEvent,
        Depends(get_record_shipment_event_use_case),
    ],
) -> ShipmentEventResponse:
    try:
        event = await use_case.execute(
            RecordShipmentEventCommand(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
                event_type=request.event_type,
                occurred_at=request.occurred_at,
                status=request.status,
                location_id=request.location_id,
                description=request.description,
                metadata=request.metadata,
                created_by_user_id=membership.user_id,
            )
        )

    except ShipmentEventShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    except ShipmentEventLocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment event location not found",
        ) from exc

    return ShipmentEventResponse.model_validate(event)


@router.get(
    "",
    response_model=list[ShipmentEventResponse],
    status_code=status.HTTP_200_OK,
)
async def list_shipment_events(
    tenant_id: UUID,
    shipment_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.SHIPMENT_EVENT_READ,
            )
        ),
    ],
    use_case: Annotated[
        ListShipmentEvents,
        Depends(get_list_shipment_events_use_case),
    ],
) -> list[ShipmentEventResponse]:
    try:
        events = await use_case.execute(
            ListShipmentEventsQuery(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
            )
        )

    except ShipmentEventShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    return [ShipmentEventResponse.model_validate(event) for event in events]
