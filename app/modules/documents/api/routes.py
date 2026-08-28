from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.documents.api.dependencies import (
    get_complete_shipment_label_use_case,
    get_create_document_use_case,
    get_create_shipment_label_use_case,
    get_get_document_use_case,
    get_get_shipment_label_use_case,
    get_list_shipment_documents_use_case,
    get_list_shipment_labels_use_case,
    get_mark_document_failed_use_case,
    get_mark_shipment_label_failed_use_case,
    get_void_shipment_label_use_case,
)
from app.modules.documents.api.schemas import (
    CompleteShipmentLabelRequest,
    CreateDocumentRequest,
    CreateShipmentLabelRequest,
    DocumentResponse,
    ShipmentLabelResponse,
)
from app.modules.documents.application.exceptions import (
    CarrierNotFoundError,
    CarrierServiceMismatchError,
    CarrierServiceNotFoundError,
    DocumentNotFoundError,
    DocumentShipmentMismatchError,
    InvalidDocumentStateTransitionError,
    InvalidShipmentLabelStateTransitionError,
    InvalidShippingLabelDocumentError,
    PackageNotFoundError,
    PackageShipmentMismatchError,
    ShipmentLabelAlreadyVoidedError,
    ShipmentLabelNotFoundError,
    ShipmentNotFoundError,
)
from app.modules.documents.application.use_cases.complete_shipment_label import (
    CompleteShipmentLabelCommand,
    CompleteShipmentLabelUseCase,
)
from app.modules.documents.application.use_cases.create_document import (
    CreateDocumentCommand,
    CreateDocumentUseCase,
)
from app.modules.documents.application.use_cases.create_shipment_label import (
    CreateShipmentLabelCommand,
    CreateShipmentLabelUseCase,
)
from app.modules.documents.application.use_cases.get_document import (
    GetDocumentQuery,
    GetDocumentUseCase,
)
from app.modules.documents.application.use_cases.get_shipment_label import (
    GetShipmentLabelQuery,
    GetShipmentLabelUseCase,
)
from app.modules.documents.application.use_cases.list_shipment_documents import (
    ListShipmentDocumentsQuery,
    ListShipmentDocumentsUseCase,
)
from app.modules.documents.application.use_cases.list_shipment_labels import (
    ListShipmentLabelsQuery,
    ListShipmentLabelsUseCase,
)
from app.modules.documents.application.use_cases.mark_document_failed import (
    MarkDocumentFailedCommand,
    MarkDocumentFailedUseCase,
)
from app.modules.documents.application.use_cases.mark_shipment_label_failed import (
    MarkShipmentLabelFailedCommand,
    MarkShipmentLabelFailedUseCase,
)
from app.modules.documents.application.use_cases.void_shipment_label import (
    VoidShipmentLabelCommand,
    VoidShipmentLabelUseCase,
)
from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership

router = APIRouter(
    prefix="/tenants/{tenant_id}",
    tags=["documents"],
)


@router.post(
    "/shipments/{shipment_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    tenant_id: UUID,
    shipment_id: UUID,
    request: CreateDocumentRequest,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.DOCUMENT_CREATE)),
    ],
    use_case: Annotated[
        CreateDocumentUseCase,
        Depends(get_create_document_use_case),
    ],
) -> DocumentResponse:
    del membership

    try:
        document = await use_case.execute(
            CreateDocumentCommand(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
                document_type=request.document_type,
                filename=request.filename,
                content_type=request.content_type,
                storage_key=request.storage_key,
            )
        )
    except ShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    return DocumentResponse.model_validate(document)


@router.get(
    "/shipments/{shipment_id}/documents",
    response_model=list[DocumentResponse],
)
async def list_shipment_documents(
    tenant_id: UUID,
    shipment_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.DOCUMENT_READ)),
    ],
    use_case: Annotated[
        ListShipmentDocumentsUseCase,
        Depends(get_list_shipment_documents_use_case),
    ],
) -> list[DocumentResponse]:
    del membership

    documents = await use_case.execute(
        ListShipmentDocumentsQuery(
            tenant_id=tenant_id,
            shipment_id=shipment_id,
        )
    )

    return [DocumentResponse.model_validate(document) for document in documents]


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    tenant_id: UUID,
    document_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.DOCUMENT_READ)),
    ],
    use_case: Annotated[
        GetDocumentUseCase,
        Depends(get_get_document_use_case),
    ],
) -> DocumentResponse:
    del membership

    try:
        document = await use_case.execute(
            GetDocumentQuery(
                tenant_id=tenant_id,
                document_id=document_id,
            )
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from exc

    return DocumentResponse.model_validate(document)


@router.post(
    "/documents/{document_id}/failed",
    response_model=DocumentResponse,
)
async def mark_document_failed(
    tenant_id: UUID,
    document_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.DOCUMENT_UPDATE)),
    ],
    use_case: Annotated[
        MarkDocumentFailedUseCase,
        Depends(get_mark_document_failed_use_case),
    ],
) -> DocumentResponse:
    del membership

    try:
        document = await use_case.execute(
            MarkDocumentFailedCommand(
                tenant_id=tenant_id,
                document_id=document_id,
            )
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from exc
    except InvalidDocumentStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid document state transition",
        ) from exc

    return DocumentResponse.model_validate(document)


@router.post(
    "/shipments/{shipment_id}/labels",
    response_model=ShipmentLabelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_shipment_label(
    tenant_id: UUID,
    shipment_id: UUID,
    request: CreateShipmentLabelRequest,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.SHIPMENT_LABEL_CREATE)),
    ],
    use_case: Annotated[
        CreateShipmentLabelUseCase,
        Depends(get_create_shipment_label_use_case),
    ],
) -> ShipmentLabelResponse:
    del membership

    try:
        shipment_label = await use_case.execute(
            CreateShipmentLabelCommand(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
                package_id=request.package_id,
                carrier_id=request.carrier_id,
                carrier_service_id=request.carrier_service_id,
            )
        )
    except ShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc
    except PackageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found",
        ) from exc
    except CarrierNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrier not found",
        ) from exc
    except CarrierServiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrier service not found",
        ) from exc
    except PackageShipmentMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Package does not belong to shipment",
        ) from exc
    except CarrierServiceMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Carrier service does not belong to carrier",
        ) from exc

    return ShipmentLabelResponse.model_validate(shipment_label)


@router.get(
    "/shipments/{shipment_id}/labels",
    response_model=list[ShipmentLabelResponse],
)
async def list_shipment_labels(
    tenant_id: UUID,
    shipment_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.SHIPMENT_LABEL_READ)),
    ],
    use_case: Annotated[
        ListShipmentLabelsUseCase,
        Depends(get_list_shipment_labels_use_case),
    ],
) -> list[ShipmentLabelResponse]:
    del membership

    shipment_labels = await use_case.execute(
        ListShipmentLabelsQuery(
            tenant_id=tenant_id,
            shipment_id=shipment_id,
        )
    )

    return [
        ShipmentLabelResponse.model_validate(shipment_label) for shipment_label in shipment_labels
    ]


@router.get(
    "/shipment-labels/{shipment_label_id}",
    response_model=ShipmentLabelResponse,
)
async def get_shipment_label(
    tenant_id: UUID,
    shipment_label_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.SHIPMENT_LABEL_READ)),
    ],
    use_case: Annotated[
        GetShipmentLabelUseCase,
        Depends(get_get_shipment_label_use_case),
    ],
) -> ShipmentLabelResponse:
    del membership

    try:
        shipment_label = await use_case.execute(
            GetShipmentLabelQuery(
                tenant_id=tenant_id,
                shipment_label_id=shipment_label_id,
            )
        )
    except ShipmentLabelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment label not found",
        ) from exc

    return ShipmentLabelResponse.model_validate(shipment_label)


@router.post(
    "/shipment-labels/{shipment_label_id}/complete",
    response_model=ShipmentLabelResponse,
)
async def complete_shipment_label(
    tenant_id: UUID,
    shipment_label_id: UUID,
    request: CompleteShipmentLabelRequest,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.SHIPMENT_LABEL_UPDATE)),
    ],
    use_case: Annotated[
        CompleteShipmentLabelUseCase,
        Depends(get_complete_shipment_label_use_case),
    ],
) -> ShipmentLabelResponse:
    del membership

    try:
        shipment_label = await use_case.execute(
            CompleteShipmentLabelCommand(
                tenant_id=tenant_id,
                shipment_label_id=shipment_label_id,
                document_id=request.document_id,
                tracking_number=request.tracking_number,
            )
        )
    except ShipmentLabelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment label not found",
        ) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from exc
    except ShipmentLabelAlreadyVoidedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shipment label is already voided",
        ) from exc
    except InvalidShipmentLabelStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid shipment label state transition",
        ) from exc
    except InvalidDocumentStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid document state transition",
        ) from exc
    except DocumentShipmentMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document does not belong to shipment",
        ) from exc
    except InvalidShippingLabelDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is not a shipping label",
        ) from exc

    return ShipmentLabelResponse.model_validate(shipment_label)


@router.post(
    "/shipment-labels/{shipment_label_id}/failed",
    response_model=ShipmentLabelResponse,
)
async def mark_shipment_label_failed(
    tenant_id: UUID,
    shipment_label_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.SHIPMENT_LABEL_UPDATE)),
    ],
    use_case: Annotated[
        MarkShipmentLabelFailedUseCase,
        Depends(get_mark_shipment_label_failed_use_case),
    ],
) -> ShipmentLabelResponse:
    del membership

    try:
        shipment_label = await use_case.execute(
            MarkShipmentLabelFailedCommand(
                tenant_id=tenant_id,
                shipment_label_id=shipment_label_id,
            )
        )
    except ShipmentLabelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment label not found",
        ) from exc
    except ShipmentLabelAlreadyVoidedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shipment label is already voided",
        ) from exc
    except InvalidShipmentLabelStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid shipment label state transition",
        ) from exc

    return ShipmentLabelResponse.model_validate(shipment_label)


@router.post(
    "/shipment-labels/{shipment_label_id}/void",
    response_model=ShipmentLabelResponse,
)
async def void_shipment_label(
    tenant_id: UUID,
    shipment_label_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.SHIPMENT_LABEL_VOID)),
    ],
    use_case: Annotated[
        VoidShipmentLabelUseCase,
        Depends(get_void_shipment_label_use_case),
    ],
) -> ShipmentLabelResponse:
    del membership

    try:
        shipment_label = await use_case.execute(
            VoidShipmentLabelCommand(
                tenant_id=tenant_id,
                shipment_label_id=shipment_label_id,
            )
        )
    except ShipmentLabelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment label not found",
        ) from exc
    except ShipmentLabelAlreadyVoidedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shipment label is already voided",
        ) from exc
    except InvalidShipmentLabelStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid shipment label state transition",
        ) from exc

    return ShipmentLabelResponse.model_validate(shipment_label)
