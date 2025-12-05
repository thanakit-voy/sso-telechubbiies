"""
Activity log endpoints.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_team_service,
    get_activity_service,
    get_current_active_user,
    require_team_admin,
)
from app.models.user import User
from app.services.team_service import TeamService
from app.services.activity_service import ActivityService
from app.schemas.activity_log import (
    ActivityLogResponse,
    ActivityLogList,
)
from app.schemas.user import UserBrief

router = APIRouter()


@router.get("", response_model=ActivityLogList)
async def list_activity_logs(
    actor_id: Optional[UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    oauth_client_id: Optional[UUID] = Query(None, description="Filter by OAuth client ID"),
    login_method: Optional[str] = Query(None, description="Filter by login method: direct or oauth"),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """
    List activity logs.

    System owners can see all logs.
    Regular users can only see their own logs.

    Supports filtering by OAuth client for login/logout events.
    """
    # Non-system owners can only see their own logs
    if not current_user.is_system_owner:
        actor_id = current_user.id

    logs = await activity_service.get_logs(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        from_date=from_date,
        to_date=to_date,
        skip=0,  # Get all first, then filter by extra_data
        limit=1000,  # Get more to filter
    )

    # Filter by OAuth client or login method if specified
    if oauth_client_id or login_method:
        filtered_logs = []
        for log in logs:
            if not log.extra_data:
                if login_method == "direct" and log.action in ["login", "logout"]:
                    # Direct login/logout may not have extra_data or login_method="direct"
                    filtered_logs.append(log)
                continue

            # Check OAuth client ID filter
            if oauth_client_id:
                log_client_id = log.extra_data.get("oauth_client_id")
                if log_client_id != str(oauth_client_id):
                    continue

            # Check login method filter
            if login_method:
                log_method = log.extra_data.get("login_method") or log.extra_data.get("logout_method")
                if log_method != login_method:
                    continue

            filtered_logs.append(log)
        logs = filtered_logs

    # Apply pagination after filtering
    total = len(logs)
    logs = logs[skip:skip + limit]

    # Re-count if we filtered
    if not oauth_client_id and not login_method:
        total = await activity_service.count_logs(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            from_date=from_date,
            to_date=to_date,
        )

    items = [
        ActivityLogResponse(
            id=log.id,
            actor=UserBrief(
                id=log.actor.id,
                email=log.actor.email,
                first_name=log.actor.first_name,
                last_name=log.actor.last_name,
            ),
            actor_team_id=log.actor_team_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            extra_data=log.extra_data,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return ActivityLogList(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/teams/{team_slug}", response_model=ActivityLogList)
async def get_team_activity_logs(
    team_slug: str,
    include_sub_teams: bool = Query(True),
    action: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """
    Get activity logs for a team.

    Includes logs from direct sub-teams if include_sub_teams is True.
    Does NOT include logs from nested sub-teams (sub-teams of sub-teams).
    """
    team = await team_service.get_team_by_slug(team_slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    logs = await activity_service.get_team_logs(
        team_id=team.id,
        include_sub_teams=include_sub_teams,
        skip=skip,
        limit=limit,
    )

    # Filter by action and date if provided
    filtered_logs = []
    for log in logs:
        if action and log.action != action:
            continue
        if from_date and log.created_at < from_date:
            continue
        if to_date and log.created_at > to_date:
            continue
        filtered_logs.append(log)

    items = [
        ActivityLogResponse(
            id=log.id,
            actor=UserBrief(
                id=log.actor.id,
                email=log.actor.email,
                first_name=log.actor.first_name,
                last_name=log.actor.last_name,
            ),
            actor_team_id=log.actor_team_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            extra_data=log.extra_data,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )
        for log in filtered_logs
    ]

    return ActivityLogList(
        items=items,
        total=len(items),
        skip=skip,
        limit=limit,
    )
