from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.entitlements.api.dependencies import get_entitlements_use_case
from app.modules.entitlements.api.schemas import EntitlementsResponse
from app.modules.entitlements.application.use_cases.get_entitlements import GetEntitlements
from app.modules.identity.api.auth_dependencies import require_permission
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.saas.application.exceptions import SubscriptionNotFoundError

router = APIRouter(
    prefix="/tenants/{tenant_id}/entitlements",
    tags=["entitlements"],
)


@router.get("", response_model=EntitlementsResponse)
async def get_entitlements(
    tenant_id: UUID,
    membership: Annotated[
        Membership,
        Depends(require_permission(Permissions.ENTITLEMENT_READ)),
    ],
    use_case: Annotated[
        GetEntitlements,
        Depends(get_entitlements_use_case),
    ],
) -> EntitlementsResponse:
    del membership

    try:
        snapshot = await use_case.execute(tenant_id)
    except SubscriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from exc

    return EntitlementsResponse(
        tenant_id=snapshot.tenant_id,
        plan_code=snapshot.plan_code,
        subscription_status=snapshot.subscription_status,
        ai_assistant=snapshot.ai_assistant,
        rag_indexing=snapshot.rag_indexing,
        outbound_webhooks=snapshot.outbound_webhooks,
        team_member_limit=snapshot.team_member_limit,
    )
