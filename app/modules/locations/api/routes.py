from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.locations.api.dependencies import (
    get_create_location_use_case,
    get_delete_location_use_case,
    get_get_location_use_case,
    get_list_locations_use_case,
    get_update_location_use_case,
)
from app.modules.locations.api.schemas import (
    CreateLocationRequest,
    LocationResponse,
    UpdateLocationRequest,
)
from app.modules.locations.application.exceptions import (
    LocationCodeAlreadyExistsError,
    LocationNotFoundError,
)
from app.modules.locations.application.use_cases.create_location import (
    CreateLocation,
    CreateLocationCommand,
)
from app.modules.locations.application.use_cases.delete_location import (
    DeleteLocation,
    DeleteLocationCommand,
)
from app.modules.locations.application.use_cases.get_location import (
    GetLocation,
    GetLocationQuery,
)
from app.modules.locations.application.use_cases.list_locations import (
    ListLocations,
    ListLocationsQuery,
)
from app.modules.locations.application.use_cases.update_location import (
    UpdateLocation,
    UpdateLocationCommand,
)

router = APIRouter(
    prefix="/tenants/{tenant_id}/locations",
    tags=["locations"],
)


@router.post(
    "",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_location(
    tenant_id: UUID,
    request: CreateLocationRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.LOCATION_CREATE,
            )
        ),
    ],
    use_case: Annotated[
        CreateLocation,
        Depends(get_create_location_use_case),
    ],
) -> LocationResponse:
    try:
        location = await use_case.execute(
            CreateLocationCommand(
                tenant_id=tenant_id,
                name=request.name,
                code=request.code,
                type=request.type,
                country_code=request.country_code,
                state=request.state,
                city=request.city,
                postal_code=request.postal_code,
                address_line1=request.address_line1,
                address_line2=request.address_line2,
                contact_name=request.contact_name,
                email=str(request.email) if request.email is not None else None,
                phone=request.phone,
                latitude=request.latitude,
                longitude=request.longitude,
                notes=request.notes,
            )
        )

    except LocationCodeAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Location code already exists",
        ) from exc

    return LocationResponse.model_validate(location)


@router.get(
    "",
    response_model=list[LocationResponse],
    status_code=status.HTTP_200_OK,
)
async def list_locations(
    tenant_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.LOCATION_READ,
            )
        ),
    ],
    use_case: Annotated[
        ListLocations,
        Depends(get_list_locations_use_case),
    ],
) -> list[LocationResponse]:
    locations = await use_case.execute(
        ListLocationsQuery(
            tenant_id=tenant_id,
        )
    )

    return [LocationResponse.model_validate(location) for location in locations]


@router.get(
    "/{location_id}",
    response_model=LocationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_location(
    tenant_id: UUID,
    location_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.LOCATION_READ,
            )
        ),
    ],
    use_case: Annotated[
        GetLocation,
        Depends(get_get_location_use_case),
    ],
) -> LocationResponse:
    try:
        location = await use_case.execute(
            GetLocationQuery(
                tenant_id=tenant_id,
                location_id=location_id,
            )
        )

    except LocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        ) from exc

    return LocationResponse.model_validate(location)


@router.patch(
    "/{location_id}",
    response_model=LocationResponse,
    status_code=status.HTTP_200_OK,
)
async def update_location(
    tenant_id: UUID,
    location_id: UUID,
    request: UpdateLocationRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.LOCATION_UPDATE,
            )
        ),
    ],
    use_case: Annotated[
        UpdateLocation,
        Depends(get_update_location_use_case),
    ],
) -> LocationResponse:
    try:
        location = await use_case.execute(
            UpdateLocationCommand(
                tenant_id=tenant_id,
                location_id=location_id,
                name=request.name,
                code=request.code,
                type=request.type,
                country_code=request.country_code,
                state=request.state,
                city=request.city,
                postal_code=request.postal_code,
                address_line1=request.address_line1,
                address_line2=request.address_line2,
                contact_name=request.contact_name,
                email=str(request.email) if request.email is not None else None,
                phone=request.phone,
                latitude=request.latitude,
                longitude=request.longitude,
                notes=request.notes,
            )
        )

    except LocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        ) from exc

    except LocationCodeAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Location code already exists",
        ) from exc

    return LocationResponse.model_validate(location)


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_location(
    tenant_id: UUID,
    location_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.LOCATION_DELETE,
            )
        ),
    ],
    use_case: Annotated[
        DeleteLocation,
        Depends(get_delete_location_use_case),
    ],
) -> Response:
    try:
        await use_case.execute(
            DeleteLocationCommand(
                tenant_id=tenant_id,
                location_id=location_id,
            )
        )

    except LocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        ) from exc

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
