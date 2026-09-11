from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.saas.api.dependencies import (
    get_change_plan_use_case,
    get_subscription_use_case,
)
from app.modules.saas.api.schemas import ChangePlanRequest, SubscriptionResponse
from app.modules.saas.application.exceptions import (
    InvalidSubscriptionTransitionError,
    SelfServicePlanUnavailableError,
    SubscriptionNotFoundError,
    SubscriptionProviderUnavailableError,
)
from app.modules.saas.application.use_cases.change_plan import (
    ChangePlan,
    ChangePlanCommand,
)
from app.modules.saas.application.use_cases.get_subscription import (
    GetSubscription,
    GetSubscriptionQuery,
)

router = APIRouter(
    prefix="/tenants/{tenant_id}/subscription",
    tags=["saas-subscription"],
)


@router.get("", response_model=SubscriptionResponse)
async def get_subscription(
    tenant_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.SUBSCRIPTION_READ)),
    ],
    use_case: Annotated[
        GetSubscription,
        Depends(get_subscription_use_case),
    ],
) -> SubscriptionResponse:
    del membership

    try:
        subscription = await use_case.execute(
            GetSubscriptionQuery(tenant_id=tenant_id),
        )
    except SubscriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from exc

    return SubscriptionResponse.model_validate(subscription)


@router.post("/plan", response_model=SubscriptionResponse)
async def change_subscription_plan(
    tenant_id: UUID,
    request: ChangePlanRequest,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.TENANT_MANAGE)),
    ],
    use_case: Annotated[
        ChangePlan,
        Depends(get_change_plan_use_case),
    ],
) -> SubscriptionResponse:
    del membership

    try:
        subscription = await use_case.execute(
            ChangePlanCommand(
                tenant_id=tenant_id,
                requested_plan=request.plan_code,
            )
        )
    except SubscriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from exc
    except SelfServicePlanUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This plan is not available for self-service activation",
        ) from exc
    except InvalidSubscriptionTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SubscriptionProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return SubscriptionResponse.model_validate(subscription)
