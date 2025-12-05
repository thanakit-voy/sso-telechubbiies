"""
Team schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, SlugMixin, TimestampMixin
from app.schemas.user import UserBrief


class TeamBase(BaseSchema, SlugMixin):
    """Base team schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)


class TeamCreate(TeamBase):
    """Schema for creating a new team."""

    parent_team_id: Optional[UUID] = None


class TeamUpdate(BaseSchema):
    """Schema for updating a team."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)


class TeamResponse(TeamBase, TimestampMixin):
    """Schema for team response."""

    id: UUID
    parent_team_id: Optional[UUID] = None
    owner_id: UUID


class TeamBrief(BaseSchema):
    """Brief team info for embedding in other responses."""

    id: UUID
    name: str
    slug: str


class TeamWithOwner(TeamResponse):
    """Team response with owner info."""

    owner: UserBrief


class TeamWithParent(TeamResponse):
    """Team response with parent team info."""

    parent_team: Optional[TeamBrief] = None


class TeamWithSubTeams(TeamResponse):
    """Team response with sub-teams."""

    sub_teams: list[TeamBrief] = []


class TeamMemberResponse(BaseSchema):
    """Schema for team member response."""

    id: UUID
    user: UserBrief
    role: Optional["RoleBrief"] = None
    joined_at: datetime
    is_admin: bool = False


class TeamWithMembers(TeamWithOwner):
    """Team response with members list."""

    members: list[TeamMemberResponse] = []
    member_count: int = 0


class RoleBrief(BaseSchema):
    """Brief role info for embedding."""

    id: UUID
    name: str
    slug: str
    is_admin: bool = False


# Update forward references
TeamMemberResponse.model_rebuild()
TeamWithMembers.model_rebuild()
