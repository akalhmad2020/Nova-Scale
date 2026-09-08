from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.database import SessionFactory
from app.modules.entitlements.application.use_cases.get_entitlements import (
    GetEntitlements,
)
from app.modules.identity.api.auth_dependencies import get_current_membership
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.saas.application.exceptions import SubscriptionNotFoundError
from app.modules.saas.infrastructure.unit_of_work import SQLAlchemySubscriptionUnitOfWork


def get_entitlements_use_case() -> GetEntitlements:
    return GetEntitlements(
        unit_of_work=SQLAlchemySubscriptionUnitOfWork(SessionFactory),
    )


def require_entitlement(entitlement_code: str) -> Callable[..., object]:
    async def dependency(
        membership: Annotated[Membership, Depends(get_current_membership)],
        use_case: Annotated[GetEntitlements, Depends(get_entitlements_use_case)],
    ) -> Membership:
        try:
            snapshot = await use_case.execute(membership.tenant_id)
        except SubscriptionNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant subscription is not provisioned",
            ) from exc

        if not snapshot.is_enabled(entitlement_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Entitlement '{entitlement_code}' is not enabled for this subscription",
            )

        return membership

    return dependency
