from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.ledger.application.exceptions import (
    LedgerAccountInactiveError,
    LedgerAccountNotFoundError,
)
from app.modules.payments.api.dependencies import (
    get_add_payment_allocation_use_case,
    get_create_payment_use_case,
    get_get_payment_use_case,
    get_list_payments_use_case,
    get_post_payment_use_case,
    get_remove_payment_allocation_use_case,
    get_void_payment_use_case,
)
from app.modules.payments.api.schemas import (
    AddPaymentAllocationRequest,
    CreatePaymentRequest,
    PaymentAllocationResponse,
    PaymentResponse,
)
from app.modules.payments.application.use_cases.add_payment_allocation import (
    AddPaymentAllocationUseCase,
)
from app.modules.payments.application.use_cases.create_payment import (
    CreatePaymentUseCase,
)
from app.modules.payments.application.use_cases.get_payment import (
    GetPaymentUseCase,
)
from app.modules.payments.application.use_cases.list_payments import (
    ListPaymentsUseCase,
)
from app.modules.payments.application.use_cases.post_payment import (
    PostPaymentUseCase,
)
from app.modules.payments.application.use_cases.remove_payment_allocation import (
    RemovePaymentAllocationUseCase,
)
from app.modules.payments.application.use_cases.void_payment import (
    VoidPaymentUseCase,
)
from app.modules.payments.domain.exceptions import (
    DuplicatePaymentAllocationError,
    DuplicatePaymentNumberError,
    InvalidInvoiceForPaymentError,
    InvalidPaymentStateTransitionError,
    PaymentAllocationExceedsInvoiceError,
    PaymentAllocationExceedsPaymentError,
    PaymentAllocationNotFoundError,
    PaymentCurrencyMismatchError,
    PaymentCustomerNotFoundError,
    PaymentNotFoundError,
    PaymentNotFullyAllocatedError,
)

router = APIRouter(
    prefix="/tenants/{tenant_id}",
    tags=["payments"],
)


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment(
    tenant_id: UUID,
    request: CreatePaymentRequest,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.PAYMENT_CREATE)),
    ],
    use_case: Annotated[
        CreatePaymentUseCase,
        Depends(get_create_payment_use_case),
    ],
) -> PaymentResponse:
    del membership

    try:
        payment = await use_case.execute(
            tenant_id=tenant_id,
            customer_id=request.customer_id,
            payment_number=request.payment_number,
            currency=request.currency,
            amount=request.amount,
            method=request.method,
            reference=request.reference,
            received_at=request.received_at,
        )
    except PaymentCustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        ) from exc
    except DuplicatePaymentNumberError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment number already exists",
        ) from exc

    return PaymentResponse.model_validate(payment)


@router.get(
    "/payments",
    response_model=list[PaymentResponse],
)
async def list_payments(
    tenant_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.PAYMENT_READ)),
    ],
    use_case: Annotated[
        ListPaymentsUseCase,
        Depends(get_list_payments_use_case),
    ],
) -> list[PaymentResponse]:
    del membership

    payments = await use_case.execute(
        tenant_id=tenant_id,
    )

    return [PaymentResponse.model_validate(payment) for payment in payments]


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
)
async def get_payment(
    tenant_id: UUID,
    payment_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.PAYMENT_READ)),
    ],
    use_case: Annotated[
        GetPaymentUseCase,
        Depends(get_get_payment_use_case),
    ],
) -> PaymentResponse:
    del membership

    try:
        payment = await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment_id,
        )
    except PaymentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        ) from exc

    return PaymentResponse.model_validate(payment)


@router.post(
    "/payments/{payment_id}/allocations",
    response_model=PaymentAllocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_payment_allocation(
    tenant_id: UUID,
    payment_id: UUID,
    request: AddPaymentAllocationRequest,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.PAYMENT_UPDATE)),
    ],
    use_case: Annotated[
        AddPaymentAllocationUseCase,
        Depends(get_add_payment_allocation_use_case),
    ],
) -> PaymentAllocationResponse:
    del membership

    try:
        allocation = await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment_id,
            invoice_id=request.invoice_id,
            amount=request.amount,
        )
    except PaymentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        ) from exc
    except InvalidInvoiceForPaymentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invoice is not available for payment",
        ) from exc
    except InvalidPaymentStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment allocations can only be modified while payment is draft",
        ) from exc
    except DuplicatePaymentAllocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment already has an allocation for this invoice",
        ) from exc
    except PaymentCurrencyMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment and invoice currencies do not match",
        ) from exc
    except PaymentAllocationExceedsPaymentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment allocations exceed payment amount",
        ) from exc
    except PaymentAllocationExceedsInvoiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment allocation exceeds invoice amount",
        ) from exc

    except PaymentNotFullyAllocatedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment must be fully allocated before posting",
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

    return PaymentAllocationResponse.model_validate(allocation)


@router.delete(
    "/payments/{payment_id}/allocations/{payment_allocation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_payment_allocation(
    tenant_id: UUID,
    payment_id: UUID,
    payment_allocation_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.PAYMENT_UPDATE)),
    ],
    use_case: Annotated[
        RemovePaymentAllocationUseCase,
        Depends(get_remove_payment_allocation_use_case),
    ],
) -> Response:
    del membership

    try:
        await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment_id,
            payment_allocation_id=payment_allocation_id,
        )
    except PaymentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        ) from exc
    except PaymentAllocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment allocation not found",
        ) from exc
    except InvalidPaymentStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment allocations can only be modified while payment is draft",
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/payments/{payment_id}/post",
    response_model=PaymentResponse,
)
async def post_payment(
    tenant_id: UUID,
    payment_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.PAYMENT_POST)),
    ],
    use_case: Annotated[
        PostPaymentUseCase,
        Depends(get_post_payment_use_case),
    ],
) -> PaymentResponse:

    try:
        payment = await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment_id,
            actor_id=membership.user_id,
        )
    except PaymentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        ) from exc
    except InvalidPaymentStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment cannot be posted in its current state",
        ) from exc
    except InvalidInvoiceForPaymentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invoice is not available for payment",
        ) from exc
    except PaymentCurrencyMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment and invoice currencies do not match",
        ) from exc
    except PaymentAllocationExceedsPaymentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment allocations exceed payment amount",
        ) from exc
    except PaymentAllocationExceedsInvoiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment allocation exceeds invoice amount",
        ) from exc
    except PaymentNotFullyAllocatedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment must be fully allocated before posting",
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

    return PaymentResponse.model_validate(payment)


@router.post(
    "/payments/{payment_id}/void",
    response_model=PaymentResponse,
)
async def void_payment(
    tenant_id: UUID,
    payment_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.PAYMENT_VOID)),
    ],
    use_case: Annotated[
        VoidPaymentUseCase,
        Depends(get_void_payment_use_case),
    ],
) -> PaymentResponse:

    try:
        payment = await use_case.execute(
            tenant_id=tenant_id,
            payment_id=payment_id,
            actor_id=membership.user_id,
        )
    except PaymentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        ) from exc
    except InvalidPaymentStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment cannot be voided in its current state",
        ) from exc

    return PaymentResponse.model_validate(payment)
