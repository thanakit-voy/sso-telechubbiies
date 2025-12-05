"""
Workspace schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, SlugMixin, TimestampMixin
from app.schemas.user import UserBrief


class WorkspaceBase(BaseSchema, SlugMixin):
    """Base workspace schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)


class WorkspaceCreate(WorkspaceBase):
    """Schema for creating a new workspace."""
    pass


class WorkspaceUpdate(BaseSchema):
    """Schema for updating a workspace."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)


class WorkspaceResponse(WorkspaceBase, TimestampMixin):
    """Schema for workspace response."""

    id: UUID
    created_by: UUID


class WorkspaceBrief(BaseSchema):
    """Brief workspace info for embedding in other responses."""

    id: UUID
    name: str
    slug: str


class WorkspaceWithCreator(WorkspaceResponse):
    """Workspace response with creator info."""

    creator: UserBrief


class WorkspaceGrant(BaseSchema):
    """Schema for granting workspace access."""

    workspace_id: UUID


class WorkspaceGrantToTeam(BaseSchema):
    """Schema for granting workspace to a team."""

    workspace_ids: list[UUID]


class WorkspaceGrantToUser(BaseSchema):
    """Schema for granting workspace to a user."""

    workspace_ids: list[UUID]
    user_id: UUID


class TeamWorkspaceResponse(BaseSchema):
    """Schema for team workspace access response."""

    workspace: WorkspaceBrief
    granted_at: datetime
    granted_by: UserBrief


class UserWorkspaceResponse(BaseSchema):
    """Schema for user workspace access response."""

    workspace: WorkspaceBrief
    team_id: UUID
    granted_at: datetime
    granted_by: UserBrief
