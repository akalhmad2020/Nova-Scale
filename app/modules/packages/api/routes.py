from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.packages.api.dependencies import (
    get_create_package_use_case,
    get_delete_package_use_case,
    get_get_package_use_case,
    get_list_packages_use_case,
    get_update_package_use_case,
)
from app.modules.packages.api.schemas import (
    CreatePackageRequest,
    PackageResponse,
    UpdatePackageRequest,
)
from app.modules.packages.application.exceptions import (
    PackageNotFoundError,
    PackageNumberAlreadyExistsError,
    PackageShipmentNotFoundError,
)
from app.modules.packages.application.use_cases.create_package import (
    CreatePackage,
    CreatePackageCommand,
)
from app.modules.packages.application.use_cases.delete_package import (
    DeletePackage,
    DeletePackageCommand,
)
from app.modules.packages.application.use_cases.get_package import (
    GetPackage,
    GetPackageQuery,
)
from app.modules.packages.application.use_cases.list_packages import (
    ListPackages,
    ListPackagesQuery,
)
from app.modules.packages.application.use_cases.update_package import (
    UpdatePackage,
    UpdatePackageCommand,
)

router = APIRouter(
    tags=["packages"],
)


@router.post(
    "/tenants/{tenant_id}/shipments/{shipment_id}/packages",
    response_model=PackageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_package(
    tenant_id: UUID,
    shipment_id: UUID,
    request: CreatePackageRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.PACKAGE_CREATE,
            )
        ),
    ],
    use_case: Annotated[
        CreatePackage,
        Depends(get_create_package_use_case),
    ],
) -> PackageResponse:
    try:
        package = await use_case.execute(
            CreatePackageCommand(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
                package_number=request.package_number,
                description=request.description,
                weight=request.weight,
                weight_unit=request.weight_unit,
                length=request.length,
                width=request.width,
                height=request.height,
                dimension_unit=request.dimension_unit,
                notes=request.notes,
            )
        )

    except PackageShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    except PackageNumberAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Package number already exists in shipment",
        ) from exc

    return PackageResponse.model_validate(package)


@router.get(
    "/tenants/{tenant_id}/shipments/{shipment_id}/packages",
    response_model=list[PackageResponse],
    status_code=status.HTTP_200_OK,
)
async def list_packages(
    tenant_id: UUID,
    shipment_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.PACKAGE_READ,
            )
        ),
    ],
    use_case: Annotated[
        ListPackages,
        Depends(get_list_packages_use_case),
    ],
) -> list[PackageResponse]:
    try:
        packages = await use_case.execute(
            ListPackagesQuery(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
            )
        )

    except PackageShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    return [PackageResponse.model_validate(package) for package in packages]


@router.get(
    "/tenants/{tenant_id}/packages/{package_id}",
    response_model=PackageResponse,
    status_code=status.HTTP_200_OK,
)
async def get_package(
    tenant_id: UUID,
    package_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.PACKAGE_READ,
            )
        ),
    ],
    use_case: Annotated[
        GetPackage,
        Depends(get_get_package_use_case),
    ],
) -> PackageResponse:
    try:
        package = await use_case.execute(
            GetPackageQuery(
                tenant_id=tenant_id,
                package_id=package_id,
            )
        )

    except PackageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found",
        ) from exc

    return PackageResponse.model_validate(package)


@router.patch(
    "/tenants/{tenant_id}/packages/{package_id}",
    response_model=PackageResponse,
    status_code=status.HTTP_200_OK,
)
async def update_package(
    tenant_id: UUID,
    package_id: UUID,
    request: UpdatePackageRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.PACKAGE_UPDATE,
            )
        ),
    ],
    use_case: Annotated[
        UpdatePackage,
        Depends(get_update_package_use_case),
    ],
) -> PackageResponse:
    try:
        package = await use_case.execute(
            UpdatePackageCommand(
                tenant_id=tenant_id,
                package_id=package_id,
                shipment_id=request.shipment_id,
                package_number=request.package_number,
                description=request.description,
                weight=request.weight,
                weight_unit=request.weight_unit,
                length=request.length,
                width=request.width,
                height=request.height,
                dimension_unit=request.dimension_unit,
                notes=request.notes,
            )
        )

    except PackageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found",
        ) from exc

    except PackageShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    except PackageNumberAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Package number already exists in shipment",
        ) from exc

    return PackageResponse.model_validate(package)


@router.delete(
    "/tenants/{tenant_id}/packages/{package_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_package(
    tenant_id: UUID,
    package_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.PACKAGE_DELETE,
            )
        ),
    ],
    use_case: Annotated[
        DeletePackage,
        Depends(get_delete_package_use_case),
    ],
) -> Response:
    try:
        await use_case.execute(
            DeletePackageCommand(
                tenant_id=tenant_id,
                package_id=package_id,
            )
        )

    except PackageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found",
        ) from exc

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
