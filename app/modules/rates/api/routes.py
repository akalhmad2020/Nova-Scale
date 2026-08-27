from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.rates.api.dependencies import (
    get_create_rate_quote_use_case,
    get_get_rate_quote_use_case,
    get_list_rate_quotes_use_case,
    get_transition_rate_quote_status_use_case,
)
from app.modules.rates.api.schemas import (
    CreateRateQuoteRequest,
    RateQuoteResponse,
    TransitionRateQuoteStatusRequest,
)
from app.modules.rates.application.exceptions import (
    InvalidRateQuoteStatusTransitionError,
    RateQuoteNotFoundError,
    RateQuoteShipmentNotFoundError,
)
from app.modules.rates.application.use_cases.create_rate_quote import (
    CreateRateQuote,
    CreateRateQuoteCommand,
)
from app.modules.rates.application.use_cases.get_rate_quote import (
    GetRateQuote,
    GetRateQuoteQuery,
)
from app.modules.rates.application.use_cases.list_rate_quotes import (
    ListRateQuotes,
    ListRateQuotesQuery,
)
from app.modules.rates.application.use_cases.transition_rate_quote_status import (
    TransitionRateQuoteStatus,
    TransitionRateQuoteStatusCommand,
)

router = APIRouter(
    tags=["rates"],
)


@router.post(
    "/tenants/{tenant_id}/shipments/{shipment_id}/rates",
    response_model=RateQuoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rate_quote(
    tenant_id: UUID,
    shipment_id: UUID,
    request: CreateRateQuoteRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.RATE_CREATE,
            )
        ),
    ],
    use_case: Annotated[
        CreateRateQuote,
        Depends(get_create_rate_quote_use_case),
    ],
) -> RateQuoteResponse:
    try:
        rate_quote = await use_case.execute(
            CreateRateQuoteCommand(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
                currency=request.currency,
                base_amount=request.base_amount,
                surcharge_amount=request.surcharge_amount,
                expires_at=request.expires_at,
            )
        )

    except RateQuoteShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    return RateQuoteResponse.model_validate(rate_quote)


@router.get(
    "/tenants/{tenant_id}/shipments/{shipment_id}/rates",
    response_model=list[RateQuoteResponse],
    status_code=status.HTTP_200_OK,
)
async def list_rate_quotes(
    tenant_id: UUID,
    shipment_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.RATE_READ,
            )
        ),
    ],
    use_case: Annotated[
        ListRateQuotes,
        Depends(get_list_rate_quotes_use_case),
    ],
) -> list[RateQuoteResponse]:
    try:
        rate_quotes = await use_case.execute(
            ListRateQuotesQuery(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
            )
        )

    except RateQuoteShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    return [RateQuoteResponse.model_validate(rate_quote) for rate_quote in rate_quotes]


@router.get(
    "/tenants/{tenant_id}/rates/{rate_quote_id}",
    response_model=RateQuoteResponse,
    status_code=status.HTTP_200_OK,
)
async def get_rate_quote(
    tenant_id: UUID,
    rate_quote_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.RATE_READ,
            )
        ),
    ],
    use_case: Annotated[
        GetRateQuote,
        Depends(get_get_rate_quote_use_case),
    ],
) -> RateQuoteResponse:
    try:
        rate_quote = await use_case.execute(
            GetRateQuoteQuery(
                tenant_id=tenant_id,
                rate_quote_id=rate_quote_id,
            )
        )

    except RateQuoteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate quote not found",
        ) from exc

    return RateQuoteResponse.model_validate(rate_quote)


@router.post(
    "/tenants/{tenant_id}/rates/{rate_quote_id}/status",
    response_model=RateQuoteResponse,
    status_code=status.HTTP_200_OK,
)
async def transition_rate_quote_status(
    tenant_id: UUID,
    rate_quote_id: UUID,
    request: TransitionRateQuoteStatusRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.RATE_MANAGE,
            )
        ),
    ],
    use_case: Annotated[
        TransitionRateQuoteStatus,
        Depends(get_transition_rate_quote_status_use_case),
    ],
) -> RateQuoteResponse:
    try:
        rate_quote = await use_case.execute(
            TransitionRateQuoteStatusCommand(
                tenant_id=tenant_id,
                rate_quote_id=rate_quote_id,
                status=request.status,
            )
        )

    except RateQuoteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate quote not found",
        ) from exc

    except InvalidRateQuoteStatusTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid rate quote status transition",
        ) from exc

    return RateQuoteResponse.model_validate(rate_quote)
