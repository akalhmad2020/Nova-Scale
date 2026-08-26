from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.modules.customers.api.dependencies import (
    get_create_customer_use_case,
    get_customer_use_case,
    get_delete_customer_use_case,
    get_list_customers_use_case,
    get_update_customer_use_case,
)
from app.modules.customers.api.schemas import (
    CreateCustomerRequest,
    CustomerResponse,
    UpdateCustomerRequest,
)
from app.modules.customers.application.exceptions import (
    CustomerCodeAlreadyExistsError,
    CustomerNotFoundError,
)
from app.modules.customers.application.use_cases.create_customer import (
    CreateCustomer,
    CreateCustomerCommand,
)
from app.modules.customers.application.use_cases.delete_customer import (
    DeleteCustomer,
    DeleteCustomerCommand,
)
from app.modules.customers.application.use_cases.get_customer import (
    GetCustomer,
    GetCustomerQuery,
)
from app.modules.customers.application.use_cases.list_customers import (
    ListCustomers,
    ListCustomersQuery,
)
from app.modules.customers.application.use_cases.update_customer import (
    UpdateCustomer,
    UpdateCustomerCommand,
)
from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership

router = APIRouter(
    prefix="/tenants/{tenant_id}/customers",
    tags=["customers"],
)


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer(
    tenant_id: UUID,
    request: CreateCustomerRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CUSTOMER_CREATE,
            )
        ),
    ],
    use_case: Annotated[
        CreateCustomer,
        Depends(get_create_customer_use_case),
    ],
) -> CustomerResponse:
    try:
        customer = await use_case.execute(
            CreateCustomerCommand(
                tenant_id=tenant_id,
                name=request.name,
                code=request.code,
                email=str(request.email) if request.email is not None else None,
                phone=request.phone,
                notes=request.notes,
            )
        )

    except CustomerCodeAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer code already exists",
        ) from exc

    return CustomerResponse.model_validate(customer)


@router.get(
    "",
    response_model=list[CustomerResponse],
    status_code=status.HTTP_200_OK,
)
async def list_customers(
    tenant_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CUSTOMER_READ,
            )
        ),
    ],
    use_case: Annotated[
        ListCustomers,
        Depends(get_list_customers_use_case),
    ],
) -> list[CustomerResponse]:
    customers = await use_case.execute(
        ListCustomersQuery(
            tenant_id=tenant_id,
        )
    )

    return [CustomerResponse.model_validate(customer) for customer in customers]


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK,
)
async def get_customer(
    tenant_id: UUID,
    customer_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CUSTOMER_READ,
            )
        ),
    ],
    use_case: Annotated[
        GetCustomer,
        Depends(get_customer_use_case),
    ],
) -> CustomerResponse:
    try:
        customer = await use_case.execute(
            GetCustomerQuery(
                tenant_id=tenant_id,
                customer_id=customer_id,
            )
        )

    except CustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        ) from exc

    return CustomerResponse.model_validate(customer)


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK,
)
async def update_customer(
    tenant_id: UUID,
    customer_id: UUID,
    request: UpdateCustomerRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CUSTOMER_UPDATE,
            )
        ),
    ],
    use_case: Annotated[
        UpdateCustomer,
        Depends(get_update_customer_use_case),
    ],
) -> CustomerResponse:
    try:
        customer = await use_case.execute(
            UpdateCustomerCommand(
                tenant_id=tenant_id,
                customer_id=customer_id,
                name=request.name,
                code=request.code,
                email=str(request.email) if request.email is not None else None,
                phone=request.phone,
                notes=request.notes,
            )
        )

    except CustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        ) from exc

    except CustomerCodeAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer code already exists",
        ) from exc

    return CustomerResponse.model_validate(customer)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_customer(
    tenant_id: UUID,
    customer_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.CUSTOMER_DELETE,
            )
        ),
    ],
    use_case: Annotated[
        DeleteCustomer,
        Depends(get_delete_customer_use_case),
    ],
) -> Response:
    try:
        await use_case.execute(
            DeleteCustomerCommand(
                tenant_id=tenant_id,
                customer_id=customer_id,
            )
        )

    except CustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        ) from exc

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
