from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.pricing.api.dependencies import (
    get_calculate_rate_quote_use_case,
    get_create_pricing_rule_use_case,
    get_deactivate_pricing_rule_use_case,
    get_get_pricing_rule_use_case,
    get_list_pricing_rules_use_case,
    get_update_pricing_rule_use_case,
)
from app.modules.pricing.api.schemas import (
    CreatePricingRuleRequest,
    PricingRuleResponse,
    UpdatePricingRuleRequest,
)
from app.modules.pricing.application.exceptions import (
    PricingRuleAlreadyInactiveError,
    PricingRuleInactiveError,
    PricingRuleInvalidValidityRangeError,
    PricingRuleNotEffectiveError,
    PricingRuleNotFoundError,
    PricingRuleServiceMismatchError,
    PricingShipmentNotFoundError,
)
from app.modules.pricing.application.use_cases.calculate_rate_quote import (
    CalculateRateQuote,
    CalculateRateQuoteCommand,
)
from app.modules.pricing.application.use_cases.create_pricing_rule import (
    CreatePricingRule,
    CreatePricingRuleCommand,
)
from app.modules.pricing.application.use_cases.deactivate_pricing_rule import (
    DeactivatePricingRule,
    DeactivatePricingRuleCommand,
)
from app.modules.pricing.application.use_cases.get_pricing_rule import (
    GetPricingRule,
    GetPricingRuleQuery,
)
from app.modules.pricing.application.use_cases.list_pricing_rules import (
    ListPricingRules,
    ListPricingRulesQuery,
)
from app.modules.pricing.application.use_cases.update_pricing_rule import (
    UNSET,
    UpdatePricingRule,
    UpdatePricingRuleCommand,
)
from app.modules.rates.api.schemas import RateQuoteResponse

router = APIRouter(
    prefix="/tenants/{tenant_id}/pricing-rules",
    tags=["pricing"],
)


@router.post(
    "",
    response_model=PricingRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pricing_rule(
    tenant_id: UUID,
    request: CreatePricingRuleRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.PRICING_RULE_CREATE,
            )
        ),
    ],
    use_case: Annotated[
        CreatePricingRule,
        Depends(get_create_pricing_rule_use_case),
    ],
) -> PricingRuleResponse:
    try:
        pricing_rule = await use_case.execute(
            CreatePricingRuleCommand(
                tenant_id=tenant_id,
                name=request.name,
                service_type=request.service_type,
                currency=request.currency,
                base_amount=request.base_amount,
                price_per_kg=request.price_per_kg,
                surcharge_amount=request.surcharge_amount,
                valid_from=request.valid_from,
                valid_until=request.valid_until,
            )
        )

    except PricingRuleInvalidValidityRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="valid_until must be later than valid_from",
        ) from exc

    return PricingRuleResponse.model_validate(pricing_rule)


@router.get(
    "",
    response_model=list[PricingRuleResponse],
    status_code=status.HTTP_200_OK,
)
async def list_pricing_rules(
    tenant_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.PRICING_RULE_READ,
            )
        ),
    ],
    use_case: Annotated[
        ListPricingRules,
        Depends(get_list_pricing_rules_use_case),
    ],
) -> list[PricingRuleResponse]:
    pricing_rules = await use_case.execute(
        ListPricingRulesQuery(
            tenant_id=tenant_id,
        )
    )

    return [PricingRuleResponse.model_validate(pricing_rule) for pricing_rule in pricing_rules]


@router.get(
    "/{pricing_rule_id}",
    response_model=PricingRuleResponse,
    status_code=status.HTTP_200_OK,
)
async def get_pricing_rule(
    tenant_id: UUID,
    pricing_rule_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.PRICING_RULE_READ,
            )
        ),
    ],
    use_case: Annotated[
        GetPricingRule,
        Depends(get_get_pricing_rule_use_case),
    ],
) -> PricingRuleResponse:
    try:
        pricing_rule = await use_case.execute(
            GetPricingRuleQuery(
                tenant_id=tenant_id,
                pricing_rule_id=pricing_rule_id,
            )
        )

    except PricingRuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing rule not found",
        ) from exc

    return PricingRuleResponse.model_validate(pricing_rule)


@router.patch(
    "/{pricing_rule_id}",
    response_model=PricingRuleResponse,
    status_code=status.HTTP_200_OK,
)
async def update_pricing_rule(
    tenant_id: UUID,
    pricing_rule_id: UUID,
    request: UpdatePricingRuleRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.PRICING_RULE_UPDATE,
            )
        ),
    ],
    use_case: Annotated[
        UpdatePricingRule,
        Depends(get_update_pricing_rule_use_case),
    ],
) -> PricingRuleResponse:
    try:
        pricing_rule = await use_case.execute(
            UpdatePricingRuleCommand(
                tenant_id=tenant_id,
                pricing_rule_id=pricing_rule_id,
                name=request.name,
                service_type=request.service_type,
                currency=request.currency,
                base_amount=request.base_amount,
                price_per_kg=request.price_per_kg,
                surcharge_amount=request.surcharge_amount,
                valid_from=(
                    request.valid_from if "valid_from" in request.model_fields_set else UNSET
                ),
                valid_until=(
                    request.valid_until if "valid_until" in request.model_fields_set else UNSET
                ),
            )
        )

    except PricingRuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing rule not found",
        ) from exc

    except PricingRuleInvalidValidityRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="valid_until must be later than valid_from",
        ) from exc

    return PricingRuleResponse.model_validate(pricing_rule)


@router.post(
    "/{pricing_rule_id}/deactivate",
    response_model=PricingRuleResponse,
    status_code=status.HTTP_200_OK,
)
async def deactivate_pricing_rule(
    tenant_id: UUID,
    pricing_rule_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.PRICING_RULE_DELETE,
            )
        ),
    ],
    use_case: Annotated[
        DeactivatePricingRule,
        Depends(get_deactivate_pricing_rule_use_case),
    ],
) -> PricingRuleResponse:
    try:
        pricing_rule = await use_case.execute(
            DeactivatePricingRuleCommand(
                tenant_id=tenant_id,
                pricing_rule_id=pricing_rule_id,
            )
        )

    except PricingRuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing rule not found",
        ) from exc

    except PricingRuleAlreadyInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pricing rule is already inactive",
        ) from exc

    return PricingRuleResponse.model_validate(pricing_rule)


@router.post(
    "/{pricing_rule_id}/shipments/{shipment_id}/quote",
    response_model=RateQuoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def calculate_rate_quote(
    tenant_id: UUID,
    pricing_rule_id: UUID,
    shipment_id: UUID,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.RATE_CREATE,
            )
        ),
    ],
    use_case: Annotated[
        CalculateRateQuote,
        Depends(get_calculate_rate_quote_use_case),
    ],
) -> RateQuoteResponse:
    try:
        rate_quote = await use_case.execute(
            CalculateRateQuoteCommand(
                tenant_id=tenant_id,
                shipment_id=shipment_id,
                pricing_rule_id=pricing_rule_id,
            )
        )

    except PricingShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        ) from exc

    except PricingRuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing rule not found",
        ) from exc

    except PricingRuleInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pricing rule is inactive",
        ) from exc

    except PricingRuleServiceMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pricing rule does not match shipment service type",
        ) from exc

    except PricingRuleNotEffectiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pricing rule is not currently effective",
        ) from exc

    return RateQuoteResponse.model_validate(rate_quote)
