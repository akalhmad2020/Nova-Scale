from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.carriers.api.dependencies import (
    get_create_carrier_service_use_case,
    get_create_carrier_use_case,
    get_deactivate_carrier_service_use_case,
    get_deactivate_carrier_use_case,
    get_get_carrier_service_use_case,
    get_get_carrier_use_case,
    get_list_carrier_services_use_case,
    get_list_carriers_use_case,
    get_update_carrier_service_use_case,
    get_update_carrier_use_case,
)
from app.modules.carriers.api.schemas import (
    CarrierResponse,
    CarrierServiceResponse,
    CreateCarrierRequest,
    CreateCarrierServiceRequest,
    UpdateCarrierRequest,
    UpdateCarrierServiceRequest,
)
from app.modules.carriers.application.exceptions import (
    CarrierAlreadyInactiveError,
    CarrierCodeAlreadyExistsError,
    CarrierInactiveError,
    CarrierNotFoundError,
    CarrierServiceAlreadyInactiveError,
    CarrierServiceCodeAlreadyExistsError,
    CarrierServiceNotFoundError,
)
from app.modules.carriers.application.use_cases.create_carrier import (
    CreateCarrier,
    CreateCarrierCommand,
)
from app.modules.carriers.application.use_cases.create_carrier_service import (
    CreateCarrierService,
    CreateCarrierServiceCommand,
)
from app.modules.carriers.application.use_cases.deactivate_carrier import (
    DeactivateCarrier,
    DeactivateCarrierCommand,
)
from app.modules.carriers.application.use_cases.deactivate_carrier_service import (
    DeactivateCarrierService,
    DeactivateCarrierServiceCommand,
)
from app.modules.carriers.application.use_cases.get_carrier import (
    GetCarrier,
    GetCarrierQuery,
)
from app.modules.carriers.application.use_cases.get_carrier_service import (
    GetCarrierService,
    GetCarrierServiceQuery,
)
from app.modules.carriers.application.use_cases.list_carrier_services import (
    ListCarrierServices,
    ListCarrierServicesQuery,
)
from app.modules.carriers.application.use_cases.list_carriers import (
    ListCarriers,
    ListCarriersQuery,
)
from app.modules.carriers.application.use_cases.update_carrier import (
    UpdateCarrier,
    UpdateCarrierCommand,
)
from app.modules.carriers.application.use_cases.update_carrier_service import (
    UpdateCarrierService,
    UpdateCarrierServiceCommand,
)
from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership

router = APIRouter(
    prefix="/tenants/{tenant_id}",
    tags=["carriers"],
)


@router.post(
    "/carriers",
    response_model=CarrierResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_carrier(
    tenant_id: UUID,
    request: CreateCarrierRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CARRIER_CREATE,
            )
        ),
    ],
    use_case: Annotated[
        CreateCarrier,
        Depends(get_create_carrier_use_case),
    ],
) -> CarrierResponse:
    try:
        carrier = await use_case.execute(
            CreateCarrierCommand(
                tenant_id=tenant_id,
                code=request.code,
                name=request.name,
            )
        )

    except CarrierCodeAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Carrier code already exists",
        ) from exc

    return CarrierResponse.model_validate(carrier)


@router.get(
    "/carriers",
    response_model=list[CarrierResponse],
    status_code=status.HTTP_200_OK,
)
async def list_carriers(
    tenant_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CARRIER_READ,
            )
        ),
    ],
    use_case: Annotated[
        ListCarriers,
        Depends(get_list_carriers_use_case),
    ],
) -> list[CarrierResponse]:
    carriers = await use_case.execute(
        ListCarriersQuery(
            tenant_id=tenant_id,
        )
    )

    return [CarrierResponse.model_validate(carrier) for carrier in carriers]


@router.get(
    "/carriers/{carrier_id}",
    response_model=CarrierResponse,
    status_code=status.HTTP_200_OK,
)
async def get_carrier(
    tenant_id: UUID,
    carrier_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CARRIER_READ,
            )
        ),
    ],
    use_case: Annotated[
        GetCarrier,
        Depends(get_get_carrier_use_case),
    ],
) -> CarrierResponse:
    try:
        carrier = await use_case.execute(
            GetCarrierQuery(
                tenant_id=tenant_id,
                carrier_id=carrier_id,
            )
        )

    except CarrierNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrier not found",
        ) from exc

    return CarrierResponse.model_validate(carrier)


@router.patch(
    "/carriers/{carrier_id}",
    response_model=CarrierResponse,
    status_code=status.HTTP_200_OK,
)
async def update_carrier(
    tenant_id: UUID,
    carrier_id: UUID,
    request: UpdateCarrierRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CARRIER_UPDATE,
            )
        ),
    ],
    use_case: Annotated[
        UpdateCarrier,
        Depends(get_update_carrier_use_case),
    ],
) -> CarrierResponse:
    try:
        carrier = await use_case.execute(
            UpdateCarrierCommand(
                tenant_id=tenant_id,
                carrier_id=carrier_id,
                code=request.code,
                name=request.name,
            )
        )

    except CarrierNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrier not found",
        ) from exc

    except CarrierCodeAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Carrier code already exists",
        ) from exc

    return CarrierResponse.model_validate(carrier)


@router.post(
    "/carriers/{carrier_id}/deactivate",
    response_model=CarrierResponse,
    status_code=status.HTTP_200_OK,
)
async def deactivate_carrier(
    tenant_id: UUID,
    carrier_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CARRIER_DELETE,
            )
        ),
    ],
    use_case: Annotated[
        DeactivateCarrier,
        Depends(get_deactivate_carrier_use_case),
    ],
) -> CarrierResponse:
    try:
        carrier = await use_case.execute(
            DeactivateCarrierCommand(
                tenant_id=tenant_id,
                carrier_id=carrier_id,
            )
        )

    except CarrierNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrier not found",
        ) from exc

    except CarrierAlreadyInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Carrier is already inactive",
        ) from exc

    return CarrierResponse.model_validate(carrier)


@router.post(
    "/carriers/{carrier_id}/services",
    response_model=CarrierServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_carrier_service(
    tenant_id: UUID,
    carrier_id: UUID,
    request: CreateCarrierServiceRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CARRIER_SERVICE_CREATE,
            )
        ),
    ],
    use_case: Annotated[
        CreateCarrierService,
        Depends(get_create_carrier_service_use_case),
    ],
) -> CarrierServiceResponse:
    try:
        carrier_service = await use_case.execute(
            CreateCarrierServiceCommand(
                tenant_id=tenant_id,
                carrier_id=carrier_id,
                code=request.code,
                name=request.name,
                service_type=request.service_type,
            )
        )

    except CarrierNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrier not found",
        ) from exc

    except CarrierInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Carrier is inactive",
        ) from exc

    except CarrierServiceCodeAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Carrier service code already exists",
        ) from exc

    return CarrierServiceResponse.model_validate(carrier_service)


@router.get(
    "/carriers/{carrier_id}/services",
    response_model=list[CarrierServiceResponse],
    status_code=status.HTTP_200_OK,
)
async def list_carrier_services(
    tenant_id: UUID,
    carrier_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CARRIER_SERVICE_READ,
            )
        ),
    ],
    use_case: Annotated[
        ListCarrierServices,
        Depends(get_list_carrier_services_use_case),
    ],
) -> list[CarrierServiceResponse]:
    try:
        carrier_services = await use_case.execute(
            ListCarrierServicesQuery(
                tenant_id=tenant_id,
                carrier_id=carrier_id,
            )
        )

    except CarrierNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrier not found",
        ) from exc

    return [
        CarrierServiceResponse.model_validate(carrier_service)
        for carrier_service in carrier_services
    ]


@router.get(
    "/carrier-services/{carrier_service_id}",
    response_model=CarrierServiceResponse,
    status_code=status.HTTP_200_OK,
)
async def get_carrier_service(
    tenant_id: UUID,
    carrier_service_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CARRIER_SERVICE_READ,
            )
        ),
    ],
    use_case: Annotated[
        GetCarrierService,
        Depends(get_get_carrier_service_use_case),
    ],
) -> CarrierServiceResponse:
    try:
        carrier_service = await use_case.execute(
            GetCarrierServiceQuery(
                tenant_id=tenant_id,
                carrier_service_id=carrier_service_id,
            )
        )

    except CarrierServiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrier service not found",
        ) from exc

    return CarrierServiceResponse.model_validate(carrier_service)


@router.patch(
    "/carrier-services/{carrier_service_id}",
    response_model=CarrierServiceResponse,
    status_code=status.HTTP_200_OK,
)
async def update_carrier_service(
    tenant_id: UUID,
    carrier_service_id: UUID,
    request: UpdateCarrierServiceRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CARRIER_SERVICE_UPDATE,
            )
        ),
    ],
    use_case: Annotated[
        UpdateCarrierService,
        Depends(get_update_carrier_service_use_case),
    ],
) -> CarrierServiceResponse:
    try:
        carrier_service = await use_case.execute(
            UpdateCarrierServiceCommand(
                tenant_id=tenant_id,
                carrier_service_id=carrier_service_id,
                code=request.code,
                name=request.name,
                service_type=request.service_type,
            )
        )

    except CarrierServiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrier service not found",
        ) from exc

    except CarrierServiceCodeAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Carrier service code already exists",
        ) from exc

    return CarrierServiceResponse.model_validate(carrier_service)


@router.post(
    "/carrier-services/{carrier_service_id}/deactivate",
    response_model=CarrierServiceResponse,
    status_code=status.HTTP_200_OK,
)
async def deactivate_carrier_service(
    tenant_id: UUID,
    carrier_service_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CARRIER_SERVICE_DELETE,
            )
        ),
    ],
    use_case: Annotated[
        DeactivateCarrierService,
        Depends(get_deactivate_carrier_service_use_case),
    ],
) -> CarrierServiceResponse:
    try:
        carrier_service = await use_case.execute(
            DeactivateCarrierServiceCommand(
                tenant_id=tenant_id,
                carrier_service_id=carrier_service_id,
            )
        )

    except CarrierServiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrier service not found",
        ) from exc

    except CarrierServiceAlreadyInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Carrier service is already inactive",
        ) from exc

    return CarrierServiceResponse.model_validate(carrier_service)
