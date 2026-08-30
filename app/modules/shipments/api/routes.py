from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.shipments.api.dependencies import (
    get_create_shipment_use_case,
    get_delete_shipment_use_case,
    get_get_shipment_use_case,
    get_list_shipments_use_case,
    get_transition_shipment_status_use_case,
    get_update_shipment_use_case,
)
from app.modules.shipments.api.schemas import (
    CreateShipmentRequest,
    ShipmentResponse,
    TransitionShipmentStatusRequest,
    UpdateShipmentRequest,
)
from app.modules.shipments.application.exceptions import (
    InvalidShipmentStatusTransitionError,
    ShipmentCustomerNotFoundError,
    ShipmentDestinationLocationNotFoundError,
    ShipmentNotFoundError,
    ShipmentOriginLocationNotFoundError,
    ShipmentTrackingNumberAlreadyExistsError,
)
from app.modules.shipments.application.use_cases.create_shipment import (
    CreateShipment,
    CreateShipmentCommand,
)
from app.modules.shipments.application.use_cases.delete_shipment import (
    DeleteShipment,
    DeleteShipmentCommand,
)
from app.modules.shipments.application.use_cases.get_shipment import (
    GetShipment,
    GetShipmentQuery,
)
from app.modules.shipments.application.use_cases.list_shipments import (
    ListShipments,
    ListShipmentsQuery,
)
from app.modules.shipments.application.use_cases.transition_shipment_status import (
    TransitionShipmentStatus,
    TransitionShipmentStatusCommand,
)
from app.modules.shipments.application.use_cases.update_shipment import (
    UpdateShipment,
    UpdateShipmentCommand,
)

router = APIRouter(
    prefix="/tenants/{tenant_id}/shipments",
    tags=["shipments"],
)


@router.post(
    "",
    response_model=ShipmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_shipment(
    tenant_id: UUID,
    request: CreateShipmentRequest,
    membership: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.SHIPMENT_CREATE,
            )
        ),
    ],
    use_case: Annotated[
        CreateShipment,
        Depends(get_create_shipment_use_case),
    ],
) -> ShipmentResponse:
    try:
        shipment = await use_case.execute(
            CreateShipmentCommand(
                tenant_id=tenant_id,
                actor_id=membership.user_id,
                customer_id=request.customer_id,
                origin_location_id=request.origin_location_id,
                destination_location_id=request.destination_location_id,
                tracking_number=request.tracking_number,
                reference=request.reference,
                service_type=request.service_type,
                description=request.description,
                weight=request.weight,
                weight_unit=request.weight_unit,
                notes=request.notes,
            )
        )

    except ShipmentTrackingNumberAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shipment tracking number already exists",
        ) from exc

    except ShipmentCustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment customer not found",
        ) from exc

    except ShipmentOriginLocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment origin location not found",
        ) from exc

    except ShipmentDestinationLocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment destination location not found",
        ) from exc

    return ShipmentResponse.model_validate(shipment)


@router.get(
    "",
    response_model=list[ShipmentResponse],
    status_code=status.HTTP_200_OK,
)
async def list_shipments(
    tenant_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.SHIPMENT_READ,
            )
        ),
    ],
    use_case: Annotated[
        ListShipments,
        Depends(get_list_shipments_use_case),
    ],
) -> list[ShipmentResponse]:
    shipments = await use_case.execute(
        ListShipmentsQuery(
            tenant_id=tenant_id,
        )
    )

    return [ShipmentResponse.model_validate(shipment) for shipment in shipments]


@router.get(
    "/{shipment_id}",
    response_model=ShipmentResponse,
    status_code=status.HTTP_200_OK,
)
async def get_shipment(
    tenant_id: UUID,
    shipment_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.SHIPMENT_READ,
            )
        ),
    ],
    use_case: Annotated[
        GetShipment,
        Depends(get_get_shipment_use_case),
    ],
) -> ShipmentResponse:
    try:
        shipment = await use_case.execute(
            GetShipmentQuery(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
            )
        )

    except ShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    return ShipmentResponse.model_validate(shipment)


@router.patch(
    "/{shipment_id}",
    response_model=ShipmentResponse,
    status_code=status.HTTP_200_OK,
)
async def update_shipment(
    tenant_id: UUID,
    shipment_id: UUID,
    request: UpdateShipmentRequest,
    membership: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.SHIPMENT_UPDATE,
            )
        ),
    ],
    use_case: Annotated[
        UpdateShipment,
        Depends(get_update_shipment_use_case),
    ],
) -> ShipmentResponse:
    try:
        shipment = await use_case.execute(
            UpdateShipmentCommand(
                tenant_id=tenant_id,
                actor_id=membership.user_id,
                shipment_id=shipment_id,
                customer_id=request.customer_id,
                origin_location_id=request.origin_location_id,
                destination_location_id=request.destination_location_id,
                tracking_number=request.tracking_number,
                reference=request.reference,
                service_type=request.service_type,
                description=request.description,
                weight=request.weight,
                weight_unit=request.weight_unit,
                notes=request.notes,
            )
        )

    except ShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    except ShipmentTrackingNumberAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shipment tracking number already exists",
        ) from exc

    except ShipmentCustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment customer not found",
        ) from exc

    except ShipmentOriginLocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment origin location not found",
        ) from exc

    except ShipmentDestinationLocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment destination location not found",
        ) from exc

    return ShipmentResponse.model_validate(shipment)


@router.delete(
    "/{shipment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_shipment(
    tenant_id: UUID,
    shipment_id: UUID,
    membership: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.SHIPMENT_DELETE,
            )
        ),
    ],
    use_case: Annotated[
        DeleteShipment,
        Depends(get_delete_shipment_use_case),
    ],
) -> Response:
    try:
        await use_case.execute(
            DeleteShipmentCommand(
                tenant_id=tenant_id,
                actor_id=membership.user_id,
                shipment_id=shipment_id,
            )
        )

    except ShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


@router.post(
    "/{shipment_id}/transition",
    response_model=ShipmentResponse,
    status_code=status.HTTP_200_OK,
)
async def transition_shipment_status(
    tenant_id: UUID,
    shipment_id: UUID,
    request: TransitionShipmentStatusRequest,
    membership: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.SHIPMENT_TRANSITION,
            )
        ),
    ],
    use_case: Annotated[
        TransitionShipmentStatus,
        Depends(get_transition_shipment_status_use_case),
    ],
) -> ShipmentResponse:
    try:
        shipment = await use_case.execute(
            TransitionShipmentStatusCommand(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
                target_status=request.status,
                actor_id=membership.user_id,
            )
        )

    except ShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    except InvalidShipmentStatusTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid shipment status transition",
        ) from exc

    return ShipmentResponse.model_validate(shipment)
