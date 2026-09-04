from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.modules.billing.api.dependencies import (
    get_add_invoice_line_use_case,
    get_create_invoice_use_case,
    get_get_invoice_use_case,
    get_issue_invoice_use_case,
    get_list_invoice_lines_use_case,
    get_list_invoices_use_case,
    get_remove_invoice_line_use_case,
    get_void_invoice_use_case,
)
from app.modules.billing.api.schemas import (
    AddInvoiceLineRequest,
    CreateInvoiceRequest,
    InvoiceLineResponse,
    InvoiceResponse,
)
from app.modules.billing.application.exceptions import (
    CustomerNotFoundError,
    InvalidInvoiceAmountError,
    InvalidInvoiceStateTransitionError,
    InvoiceHasNoLinesError,
    InvoiceLedgerEntryNotFoundError,
    InvoiceLineNotFoundError,
    InvoiceNotEditableError,
    InvoiceNotFoundError,
    InvoiceNumberAlreadyExistsError,
    ShipmentNotFoundError,
)
from app.modules.billing.application.use_cases.add_invoice_line import (
    AddInvoiceLineUseCase,
)
from app.modules.billing.application.use_cases.create_invoice import (
    CreateInvoiceUseCase,
)
from app.modules.billing.application.use_cases.get_invoice import (
    GetInvoiceUseCase,
)
from app.modules.billing.application.use_cases.issue_invoice import (
    IssueInvoiceUseCase,
)
from app.modules.billing.application.use_cases.list_invoice_lines import (
    ListInvoiceLinesUseCase,
)
from app.modules.billing.application.use_cases.list_invoices import (
    ListInvoicesUseCase,
)
from app.modules.billing.application.use_cases.remove_invoice_line import (
    RemoveInvoiceLineUseCase,
)
from app.modules.billing.application.use_cases.void_invoice import (
    VoidInvoiceUseCase,
)
from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.ledger.application.exceptions import (
    LedgerAccountInactiveError,
    LedgerAccountNotFoundError,
)

router = APIRouter(
    prefix="/tenants/{tenant_id}",
    tags=["billing"],
)


@router.post(
    "/invoices",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invoice(
    tenant_id: UUID,
    request: CreateInvoiceRequest,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.INVOICE_CREATE)),
    ],
    use_case: Annotated[
        CreateInvoiceUseCase,
        Depends(get_create_invoice_use_case),
    ],
) -> InvoiceResponse:
    del membership

    try:
        invoice = await use_case.execute(
            tenant_id=tenant_id,
            customer_id=request.customer_id,
            invoice_number=request.invoice_number,
            currency=request.currency,
            tax_amount=request.tax_amount,
        )
    except CustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        ) from exc
    except InvoiceNumberAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invoice number already exists",
        ) from exc
    except InvalidInvoiceAmountError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return InvoiceResponse.model_validate(invoice)


@router.get(
    "/invoices",
    response_model=list[InvoiceResponse],
)
async def list_invoices(
    tenant_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.INVOICE_READ)),
    ],
    use_case: Annotated[
        ListInvoicesUseCase,
        Depends(get_list_invoices_use_case),
    ],
) -> list[InvoiceResponse]:
    del membership

    invoices = await use_case.execute(
        tenant_id=tenant_id,
    )

    return [InvoiceResponse.model_validate(invoice) for invoice in invoices]


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
)
async def get_invoice(
    tenant_id: UUID,
    invoice_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.INVOICE_READ)),
    ],
    use_case: Annotated[
        GetInvoiceUseCase,
        Depends(get_get_invoice_use_case),
    ],
) -> InvoiceResponse:
    del membership

    try:
        invoice = await use_case.execute(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
        )
    except InvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        ) from exc

    return InvoiceResponse.model_validate(invoice)


@router.post(
    "/invoices/{invoice_id}/lines",
    response_model=InvoiceLineResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_invoice_line(
    tenant_id: UUID,
    invoice_id: UUID,
    request: AddInvoiceLineRequest,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.INVOICE_UPDATE)),
    ],
    use_case: Annotated[
        AddInvoiceLineUseCase,
        Depends(get_add_invoice_line_use_case),
    ],
) -> InvoiceLineResponse:
    del membership

    try:
        invoice_line = await use_case.execute(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            shipment_id=request.shipment_id,
            description=request.description,
            quantity=request.quantity,
            unit_price=request.unit_price,
        )
    except InvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        ) from exc
    except ShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc
    except InvoiceNotEditableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invoice is not editable",
        ) from exc
    except InvalidInvoiceAmountError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return InvoiceLineResponse.model_validate(invoice_line)


@router.delete(
    "/invoices/{invoice_id}/lines/{invoice_line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_invoice_line(
    tenant_id: UUID,
    invoice_id: UUID,
    invoice_line_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.INVOICE_UPDATE)),
    ],
    use_case: Annotated[
        RemoveInvoiceLineUseCase,
        Depends(get_remove_invoice_line_use_case),
    ],
) -> Response:
    del membership

    try:
        await use_case.execute(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            invoice_line_id=invoice_line_id,
        )
    except InvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        ) from exc
    except InvoiceLineNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice line not found",
        ) from exc
    except InvoiceNotEditableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invoice is not editable",
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/invoices/{invoice_id}/issue",
    response_model=InvoiceResponse,
)
async def issue_invoice(
    tenant_id: UUID,
    invoice_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.INVOICE_ISSUE)),
    ],
    use_case: Annotated[
        IssueInvoiceUseCase,
        Depends(get_issue_invoice_use_case),
    ],
) -> InvoiceResponse:
    try:
        invoice = await use_case.execute(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            actor_id=membership.user_id,
        )
    except InvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        ) from exc
    except InvoiceHasNoLinesError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invoice must contain at least one line before issuing",
        ) from exc
    except InvalidInvoiceStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid invoice state transition",
        ) from exc
    except LedgerAccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Required ledger account was not found",
        ) from exc
    except LedgerAccountInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Required ledger account is inactive",
        ) from exc

    return InvoiceResponse.model_validate(invoice)


@router.post(
    "/invoices/{invoice_id}/void",
    response_model=InvoiceResponse,
)
async def void_invoice(
    tenant_id: UUID,
    invoice_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.INVOICE_VOID)),
    ],
    use_case: Annotated[
        VoidInvoiceUseCase,
        Depends(get_void_invoice_use_case),
    ],
) -> InvoiceResponse:
    try:
        invoice = await use_case.execute(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            actor_id=membership.user_id,
        )
    except InvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        ) from exc
    except InvalidInvoiceStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid invoice state transition",
        ) from exc
    except InvoiceLedgerEntryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Issued invoice ledger entry is inconsistent",
        ) from exc

    return InvoiceResponse.model_validate(invoice)


@router.get(
    "/invoices/{invoice_id}/lines",
    response_model=list[InvoiceLineResponse],
)
async def list_invoice_lines(
    tenant_id: UUID,
    invoice_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.INVOICE_READ)),
    ],
    use_case: Annotated[
        ListInvoiceLinesUseCase,
        Depends(get_list_invoice_lines_use_case),
    ],
) -> list[InvoiceLineResponse]:
    del membership

    try:
        invoice_lines = await use_case.execute(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
        )
    except InvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        ) from exc

    return [InvoiceLineResponse.model_validate(invoice_line) for invoice_line in invoice_lines]
