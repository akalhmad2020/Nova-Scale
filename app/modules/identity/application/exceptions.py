class IdentityError(Exception):
    """Base exception for identity application errors."""


class EmailAlreadyRegisteredError(IdentityError):
    """Raised when an email address is already registered."""


class InvalidCredentialsError(IdentityError):
    """Raised when login credentials are invalid."""


class InactiveUserError(IdentityError):
    """Raised when a user account is inactive."""


class InvalidRefreshTokenError(IdentityError):
    """Raised when a refresh token is invalid or unusable."""


class TenantNotFoundError(IdentityError):
    """Raised when a tenant cannot be found."""


class MembershipNotFoundError(IdentityError):
    """Raised when a user is not a member of the requested tenant."""


class InactiveMembershipError(IdentityError):
    """Raised when a membership is not active."""


class InactiveTenantError(IdentityError):
    """Raised when a tenant is not active."""


class PermissionDeniedError(IdentityError):
    """Raised when a role does not have the required permission."""


class TenantSlugAlreadyExistsError(IdentityError):
    """Raised when a tenant slug is already in use."""


class InvitationAlreadyPendingError(IdentityError):
    """Raised when a pending invitation already exists."""


class UserAlreadyMemberError(IdentityError):
    """Raised when the invited user is already a tenant member."""


class RoleNotFoundError(IdentityError):
    """Raised when the requested role does not exist."""


class InvitationNotFoundError(IdentityError):
    """Raised when an invitation cannot be found."""


class InvitationNotPendingError(IdentityError):
    """Raised when an invitation is no longer pending."""


class InvitationExpiredError(IdentityError):
    """Raised when an invitation has expired."""


class InvitationEmailMismatchError(IdentityError):
    """Raised when the invitation email does not match the current user."""


class MembershipTenantMismatchError(IdentityError):
    """Raised when a membership does not belong to the requested tenant."""


class CannotSuspendSelfError(IdentityError):
    """Raised when a user attempts to suspend their own membership."""


class CannotSuspendLastOwnerError(IdentityError):
    """Raised when attempting to suspend the tenant's last active owner."""


class CannotRemoveSelfError(IdentityError):
    """Raised when a user attempts to remove their own membership."""


class CannotRemoveLastOwnerError(IdentityError):
    """Raised when attempting to remove the tenant's last active owner."""
