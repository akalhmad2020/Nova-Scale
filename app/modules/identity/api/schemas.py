from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.identity.domain.enums import InvitationStatus, MembershipStatus


class RegisterUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=12,
        max_length=128,
    )
    first_name: str = Field(
        min_length=1,
        max_length=100,
    )
    last_name: str = Field(
        min_length=1,
        max_length=100,
    )


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=1,
        max_length=128,
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(
        min_length=1,
        max_length=512,
    )


class LogoutRequest(BaseModel):
    refresh_token: str = Field(
        min_length=1,
        max_length=512,
    )


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    user_id: UUID
    role_id: UUID
    status: MembershipStatus


class CreateTenantRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )
    slug: str = Field(
        min_length=1,
        max_length=100,
    )


class CreateTenantResponse(BaseModel):
    id: UUID
    membership_id: UUID
    name: str
    slug: str


class UserTenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    membership_id: UUID
    role_id: UUID


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role_id: UUID


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    role_id: UUID
    email: str
    status: InvitationStatus
    expires_at: datetime
    accepted_at: datetime | None


class TenantMemberResponse(BaseModel):
    membership_id: UUID
    user_id: UUID
    email: str
    first_name: str
    last_name: str
    role_id: UUID


class ChangeMemberRoleRequest(BaseModel):
    role_id: UUID
