"""
Role schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, SlugMixin, TimestampMixin


class RoleBase(BaseSchema, SlugMixin):
    """Base role schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)


class RoleCreate(RoleBase):
    """Schema for creating a new role."""

    is_admin: bool = False
    priority: int = Field(default=0, ge=0, description="Role priority (higher = more important)")


class RoleUpdate(BaseSchema):
    """Schema for updating a role."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    is_admin: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, description="Role priority (higher = more important)")


class RoleResponse(RoleBase, TimestampMixin):
    """Schema for role response."""

    id: UUID
    team_id: UUID
    team_name: Optional[str] = None
    team_slug: Optional[str] = None
    is_admin: bool
    priority: int = 0


class RoleBrief(BaseSchema):
    """Brief role info for embedding in other responses."""

    id: UUID
    name: str
    slug: str
    is_admin: bool = False
    priority: int = 0


class RoleWithPermissions(RoleResponse):
    """Role response with permissions list."""

    permissions: list["PermissionBrief"] = []


class PermissionBrief(BaseSchema):
    """Brief permission info for embedding."""

    id: UUID
    name: str
    slug: str


class RolePermissionAssign(BaseSchema):
    """Schema for assigning permissions to a role."""

    permission_ids: list[UUID]


class RolePriorityReorder(BaseSchema):
    """Schema for reordering role priorities."""

    role_ids: list[UUID]  # Ordered list of role IDs (highest priority first)


class RoleWithMemberCount(RoleResponse):
    """Role response with member count for reorder validation."""

    member_count: int = 0


# Update forward references
RoleWithPermissions.model_rebuild()
