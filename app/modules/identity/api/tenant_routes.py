from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.modules.identity.api.auth_dependencies import (
    get_current_membership,
    get_current_user,
    require_permission,
)
from app.modules.identity.api.dependencies import (
    get_change_member_role_use_case,
    get_create_tenant_use_case,
    get_invite_member_use_case,
    get_list_tenant_members_use_case,
    get_list_user_tenants_use_case,
    get_remove_membership_use_case,
    get_suspend_membership_use_case,
)
from app.modules.identity.api.schemas import (
    ChangeMemberRoleRequest,
    CreateTenantRequest,
    CreateTenantResponse,
    InvitationResponse,
    InviteMemberRequest,
    MembershipResponse,
    TenantMemberResponse,
    UserTenantResponse,
)
from app.modules.identity.application.exceptions import (
    CannotRemoveLastOwnerError,
    CannotRemoveSelfError,
    CannotSuspendLastOwnerError,
    CannotSuspendSelfError,
    InvitationAlreadyPendingError,
    MembershipNotFoundError,
    MembershipTenantMismatchError,
    RoleNotFoundError,
    TenantSlugAlreadyExistsError,
    UserAlreadyMemberError,
)
from app.modules.identity.application.use_cases.change_member_role import (
    ChangeMemberRole,
    ChangeMemberRoleCommand,
)
from app.modules.identity.application.use_cases.create_tenant import (
    CreateTenant,
    CreateTenantCommand,
)
from app.modules.identity.application.use_cases.invite_member import (
    InviteMember,
    InviteMemberCommand,
)
from app.modules.identity.application.use_cases.list_tenant_members import (
    ListTenantMembers,
)
from app.modules.identity.application.use_cases.list_user_tenants import (
    ListUserTenants,
)
from app.modules.identity.application.use_cases.remove_membership import (
    RemoveMembership,
    RemoveMembershipCommand,
)
from app.modules.identity.application.use_cases.suspend_membership import (
    SuspendMembership,
    SuspendMembershipCommand,
)
from app.modules.identity.domain.permissions import Permissions
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.user import User

router = APIRouter(
    prefix="/tenants",
    tags=["tenants"],
)


@router.post(
    "",
    response_model=CreateTenantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tenant(
    request: CreateTenantRequest,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    use_case: Annotated[
        CreateTenant,
        Depends(get_create_tenant_use_case),
    ],
) -> CreateTenantResponse:
    try:
        result = await use_case.execute(
            CreateTenantCommand(
                user_id=current_user.id,
                name=request.name,
                slug=request.slug,
            )
        )
    except TenantSlugAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant slug already exists",
        ) from exc

    return CreateTenantResponse(
        id=result.tenant_id,
        membership_id=result.membership_id,
        name=result.name,
        slug=result.slug,
    )


@router.get(
    "/{tenant_id}/membership",
    response_model=MembershipResponse,
    status_code=status.HTTP_200_OK,
)
async def get_my_membership(
    tenant_id: UUID,
    membership: Annotated[
        Membership,
        Depends(get_current_membership),
    ],
) -> MembershipResponse:
    return MembershipResponse.model_validate(membership)


@router.get(
    "/{tenant_id}/permission-check",
    status_code=status.HTTP_200_OK,
)
async def permission_check(
    tenant_id: UUID,
    membership: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.TENANT_READ,
            )
        ),
    ],
) -> dict[str, str]:
    return {
        "status": "allowed",
        "tenant_id": str(tenant_id),
        "membership_id": str(membership.id),
    }


@router.get(
    "",
    response_model=list[UserTenantResponse],
    status_code=status.HTTP_200_OK,
)
async def list_my_tenants(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    use_case: Annotated[
        ListUserTenants,
        Depends(get_list_user_tenants_use_case),
    ],
) -> list[UserTenantResponse]:
    results = await use_case.execute(current_user.id)

    return [
        UserTenantResponse(
            id=item.tenant.id,
            name=item.tenant.name,
            slug=item.tenant.slug,
            membership_id=item.membership_id,
            role_id=item.role_id,
        )
        for item in results
    ]


@router.post(
    "/{tenant_id}/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    tenant_id: UUID,
    request: InviteMemberRequest,
    membership: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.MEMBERSHIP_MANAGE,
            )
        ),
    ],
    use_case: Annotated[
        InviteMember,
        Depends(get_invite_member_use_case),
    ],
) -> InvitationResponse:
    try:
        invitation = await use_case.execute(
            InviteMemberCommand(
                tenant_id=tenant_id,
                email=str(request.email),
                role_id=request.role_id,
            )
        )
    except InvitationAlreadyPendingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists",
        ) from exc
    except UserAlreadyMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this tenant",
        ) from exc
    except RoleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        ) from exc

    return InvitationResponse.model_validate(invitation)


@router.get(
    "/{tenant_id}/members",
    response_model=list[TenantMemberResponse],
    status_code=status.HTTP_200_OK,
)
async def list_tenant_members(
    tenant_id: UUID,
    membership: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.MEMBERSHIP_READ,
            )
        ),
    ],
    use_case: Annotated[
        ListTenantMembers,
        Depends(get_list_tenant_members_use_case),
    ],
) -> list[TenantMemberResponse]:
    members = await use_case.execute(tenant_id)

    return [
        TenantMemberResponse(
            membership_id=item.membership.id,
            user_id=item.user.id,
            email=item.user.email,
            first_name=item.user.first_name,
            last_name=item.user.last_name,
            role_id=item.membership.role_id,
        )
        for item in members
    ]


@router.patch(
    "/{tenant_id}/members/{membership_id}/role",
    response_model=MembershipResponse,
    status_code=status.HTTP_200_OK,
)
async def change_member_role(
    tenant_id: UUID,
    membership_id: UUID,
    request: ChangeMemberRoleRequest,
    _: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.MEMBERSHIP_MANAGE,
            )
        ),
    ],
    use_case: Annotated[
        ChangeMemberRole,
        Depends(get_change_member_role_use_case),
    ],
) -> MembershipResponse:
    try:
        membership = await use_case.execute(
            ChangeMemberRoleCommand(
                tenant_id=tenant_id,
                membership_id=membership_id,
                role_id=request.role_id,
            )
        )

    except (
        MembershipNotFoundError,
        MembershipTenantMismatchError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        ) from exc

    except RoleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        ) from exc

    return MembershipResponse.model_validate(membership)


@router.patch(
    "/{tenant_id}/members/{membership_id}/suspend",
    response_model=MembershipResponse,
    status_code=status.HTTP_200_OK,
)
async def suspend_membership(
    tenant_id: UUID,
    membership_id: UUID,
    current_membership: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.MEMBERSHIP_MANAGE,
            )
        ),
    ],
    use_case: Annotated[
        SuspendMembership,
        Depends(get_suspend_membership_use_case),
    ],
) -> MembershipResponse:
    try:
        membership = await use_case.execute(
            SuspendMembershipCommand(
                tenant_id=tenant_id,
                membership_id=membership_id,
                actor_user_id=current_membership.user_id,
            )
        )

    except (
        MembershipNotFoundError,
        MembershipTenantMismatchError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        ) from exc

    except CannotSuspendSelfError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot suspend your own membership",
        ) from exc

    except CannotSuspendLastOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The last active owner cannot be suspended",
        ) from exc

    return MembershipResponse.model_validate(membership)


@router.delete(
    "/{tenant_id}/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_membership(
    tenant_id: UUID,
    membership_id: UUID,
    current_membership: Annotated[
        Membership,
        Depends(
            require_permission(
                Permissions.MEMBERSHIP_MANAGE,
            )
        ),
    ],
    use_case: Annotated[
        RemoveMembership,
        Depends(get_remove_membership_use_case),
    ],
) -> Response:
    try:
        await use_case.execute(
            RemoveMembershipCommand(
                tenant_id=tenant_id,
                membership_id=membership_id,
                actor_user_id=current_membership.user_id,
            )
        )

    except (
        MembershipNotFoundError,
        MembershipTenantMismatchError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        ) from exc

    except CannotRemoveSelfError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot remove your own membership",
        ) from exc

    except CannotRemoveLastOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove the last active owner",
        ) from exc

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
