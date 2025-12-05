"""
Authentication schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema
from app.schemas.user import UserResponse


class LoginRequest(BaseSchema):
    """Schema for login request."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseSchema):
    """Schema for token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenWithRefresh(TokenResponse):
    """Schema for token response with refresh token."""

    refresh_token: str


class RefreshRequest(BaseSchema):
    """Schema for token refresh request."""

    refresh_token: str


class TokenPayload(BaseSchema):
    """Schema for decoded token payload."""

    sub: str  # user_id
    exp: datetime
    iat: datetime
    type: str  # 'access' or 'refresh'


class AuthResponse(BaseSchema):
    """Schema for authentication response."""

    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class SessionInfo(BaseSchema):
    """Schema for current session info."""

    user: UserResponse
    is_system_owner: bool
    teams: list["TeamMembershipInfo"] = []
    permissions: list[str] = []


class TeamMembershipInfo(BaseSchema):
    """Schema for team membership in session."""

    id: UUID
    name: str
    slug: str
    role_name: Optional[str] = None
    role_slug: Optional[str] = None
    is_admin: bool = False


class PasswordChange(BaseSchema):
    """Schema for password change request."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class SystemStatus(BaseSchema):
    """Schema for system status response."""

    initialized: bool
    user_count: int
    message: str


# Update forward references
SessionInfo.model_rebuild()
