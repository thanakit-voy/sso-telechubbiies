"""
Activity log schemas for API requests and responses.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, PaginatedResponse
from app.schemas.user import UserBrief


class ActivityLogResponse(BaseSchema):
    """Schema for activity log response."""

    id: UUID
    actor: UserBrief
    actor_team_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    extra_data: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime


class ActivityLogFilter(BaseSchema):
    """Schema for filtering activity logs."""

    actor_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class ActivityLogList(PaginatedResponse):
    """Schema for paginated activity log list."""

    items: list[ActivityLogResponse]


class ActivityLogCreate(BaseSchema):
    """Schema for creating an activity log (internal use)."""

    actor_id: UUID
    actor_team_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    extra_data: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
