"""
Invitation schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema
from app.schemas.user import UserBrief


class BootstrapRequest(BaseSchema):
    """Schema for system owner bootstrap request."""

    email: EmailStr


class BootstrapResponse(BaseSchema):
    """Schema for bootstrap response."""

    message: str
    invitation_token: Optional[str] = None  # Only in dev mode


class InvitationCreate(BaseSchema):
    """Schema for creating a team invitation."""

    email: EmailStr
    role_id: Optional[UUID] = None
    send_email: bool = True


class InvitationAccept(BaseSchema):
    """Schema for accepting an invitation."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    avatar_url: Optional[str] = Field(None, max_length=500)


class InvitationResponse(BaseSchema):
    """Schema for invitation response."""

    id: UUID
    email: str
    invitation_type: str
    team_id: Optional[UUID] = None
    role_id: Optional[UUID] = None
    status: str
    expires_at: datetime
    created_at: datetime


class InvitationWithTeam(InvitationResponse):
    """Invitation response with team info."""

    team_name: Optional[str] = None
    team_slug: Optional[str] = None
    role_name: Optional[str] = None
    invited_by: Optional[UserBrief] = None


class InvitationValidation(BaseSchema):
    """Schema for invitation validation response."""

    valid: bool
    email: str
    invitation_type: str
    team_name: Optional[str] = None
    role_name: Optional[str] = None
    expires_at: datetime
    message: Optional[str] = None


class InvitationLink(BaseSchema):
    """Schema for invitation link response."""

    invitation_id: UUID
    link: str
    expires_at: datetime
