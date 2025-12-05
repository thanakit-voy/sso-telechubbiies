"""
Permission schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, SlugMixin, TimestampMixin
from app.schemas.user import UserBrief


class PermissionBase(BaseSchema, SlugMixin):
    """Base permission schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)


class PermissionCreate(PermissionBase):
    """Schema for creating a new permission."""

    team_id: Optional[UUID] = None  # NULL for global permissions


class PermissionUpdate(BaseSchema):
    """Schema for updating a permission."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)


class PermissionResponse(PermissionBase, TimestampMixin):
    """Schema for permission response."""

    id: UUID
    team_id: Optional[UUID] = None
    is_global: bool = False


class PermissionBrief(BaseSchema):
    """Brief permission info for embedding in other responses."""

    id: UUID
    name: str
    slug: str


class PermissionGrantToTeam(BaseSchema):
    """Schema for granting permissions to a team."""

    permission_ids: list[UUID]


class TeamPermissionResponse(BaseSchema):
    """Schema for team permission access response."""

    permission: PermissionBrief
    granted_at: datetime
    granted_by: UserBrief
