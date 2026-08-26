from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.identity.api.auth_dependencies import get_current_user
from app.modules.identity.api.dependencies import (
    get_accept_invitation_use_case,
)
from app.modules.identity.api.schemas import MembershipResponse
from app.modules.identity.application.exceptions import (
    InvitationEmailMismatchError,
    InvitationExpiredError,
    InvitationNotFoundError,
    InvitationNotPendingError,
    UserAlreadyMemberError,
)
from app.modules.identity.application.use_cases.accept_invitation import (
    AcceptInvitation,
    AcceptInvitationCommand,
)
from app.modules.identity.infrastructure.models.user import User

router = APIRouter(
    prefix="/invitations",
    tags=["invitations"],
)


@router.post(
    "/{invitation_id}/accept",
    response_model=MembershipResponse,
    status_code=status.HTTP_200_OK,
)
async def accept_invitation(
    invitation_id: UUID,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    use_case: Annotated[
        AcceptInvitation,
        Depends(get_accept_invitation_use_case),
    ],
) -> MembershipResponse:
    try:
        membership = await use_case.execute(
            AcceptInvitationCommand(
                invitation_id=invitation_id,
                user_id=current_user.id,
                user_email=current_user.email,
            )
        )

    except InvitationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        ) from exc

    except InvitationNotPendingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation is no longer pending",
        ) from exc

    except InvitationExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired",
        ) from exc

    except InvitationEmailMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invitation does not belong to the current user",
        ) from exc

    except UserAlreadyMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this tenant",
        ) from exc

    return MembershipResponse.model_validate(membership)
