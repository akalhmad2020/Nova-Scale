from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.saas.api.dependencies import get_subscription_use_case
from app.modules.saas.api.schemas import SubscriptionResponse
from app.modules.saas.application.exceptions import SubscriptionNotFoundError
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
