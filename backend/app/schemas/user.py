"""
User schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import BaseSchema, TimestampMixin


class UserBase(BaseSchema):
    """Base user schema with common fields."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """Schema for creating a new user (via invitation)."""

    password: str = Field(..., min_length=8, max_length=128)
    avatar_url: Optional[str] = Field(None, max_length=500)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseSchema):
    """Schema for updating user profile."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)


class PasswordChange(BaseSchema):
    """Schema for changing password."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(BaseSchema, TimestampMixin):
    """Schema for user response."""

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    avatar_path: Optional[str] = None
    is_system_owner: bool
    is_active: bool

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def avatar(self) -> Optional[str]:
        return self.avatar_url or self.avatar_path


class UserInDB(UserResponse):
    """Schema for user with sensitive data (internal use)."""

    password_hash: Optional[str] = None


class UserBrief(BaseSchema):
    """Brief user info for embedding in other responses."""

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None


class UserWithTeams(UserResponse):
    """User response with team memberships."""

    teams: list["TeamMembershipBrief"] = []


class TeamMembershipBrief(BaseSchema):
    """Brief team membership info."""

    team_id: UUID
    team_name: str
    team_slug: str
    role_name: Optional[str] = None
    role_slug: Optional[str] = None
    is_admin: bool = False


# Update forward references
UserWithTeams.model_rebuild()
