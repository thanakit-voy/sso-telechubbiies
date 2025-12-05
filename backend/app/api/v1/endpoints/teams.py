"""
Team management endpoints.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import (
    get_team_service,
    get_activity_service,
    get_current_active_user,
    get_current_system_owner,
    get_client_ip,
    require_team_admin,
)
from app.models.user import User
from app.services.team_service import TeamService
from app.services.activity_service import ActivityService
from app.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamWithMembers,
    TeamWithOwner,
    TeamBrief,
    TeamMemberResponse,
    RoleBrief,
)
from app.schemas.user import UserBrief

router = APIRouter()


@router.get("", response_model=List[TeamWithOwner])
async def list_teams(
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
):
    """
    List teams the current user has access to.

    System owners can see all teams.
    """
    if current_user.is_system_owner:
        # Get all root teams for system owner
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.db.session import async_session_maker
        from app.models.team import Team

        async with async_session_maker() as db:
            result = await db.execute(
                select(Team)
                .options(selectinload(Team.owner))
                .where(Team.parent_team_id.is_(None))
            )
            teams = result.scalars().all()
    else:
        teams = await team_service.get_user_teams(current_user.id)

    return [
        TeamWithOwner(
            id=t.id,
            name=t.name,
            slug=t.slug,
            description=t.description,
            parent_team_id=t.parent_team_id,
            owner_id=t.owner_id,
            created_at=t.created_at,
            updated_at=t.updated_at,
            owner=UserBrief(
                id=t.owner.id,
                email=t.owner.email,
                first_name=t.owner.first_name,
                last_name=t.owner.last_name,
            ),
        )
        for t in teams
    ]


@router.post("", response_model=TeamResponse)
async def create_team(
    request: Request,
    data: TeamCreate,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """
    Create a new team.

    System owners can create root teams.
    Team admins can create sub-teams under their team.
    """
    # Check slug uniqueness
    if await team_service.slug_exists(data.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slug already exists",
        )

    # Validate parent team and permissions
    if data.parent_team_id:
        parent = await team_service.get_team_by_id(data.parent_team_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent team not found",
            )

        # Check if user can create sub-team
        if not current_user.is_system_owner:
            is_admin = await team_service.is_team_admin(parent.id, current_user.id)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required to create sub-teams",
                )
    else:
        # Only system owner can create root teams
        if not current_user.is_system_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system owner can create root teams",
            )

    # Create team
    team = await team_service.create_team(
        name=data.name,
        slug=data.slug,
        description=data.description,
        owner_id=current_user.id,
        parent_team_id=data.parent_team_id,
    )

    # Log activity
    await activity_service.log_team_created(
        actor_id=current_user.id,
        team_id=team.id,
        team_name=team.name,
        actor_team_id=data.parent_team_id,
        ip_address=get_client_ip(request),
    )

    return TeamResponse.model_validate(team)


@router.get("/{slug}", response_model=TeamWithMembers)
async def get_team(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
):
    """
    Get team details with members.
    """
    team = await team_service.get_team_with_members(
        (await team_service.get_team_by_slug(slug)).id
        if await team_service.get_team_by_slug(slug) else None
    )

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check access
    if not current_user.is_system_owner:
        member = await team_service.get_team_member(team.id, current_user.id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this team",
            )

    members = [
        TeamMemberResponse(
            id=m.id,
            user=UserBrief(
                id=m.user.id,
                email=m.user.email,
                first_name=m.user.first_name,
                last_name=m.user.last_name,
                avatar_url=m.user.avatar_url,
            ),
            role=RoleBrief(
                id=m.role.id,
                name=m.role.name,
                slug=m.role.slug,
                is_admin=m.role.is_admin,
            ) if m.role else None,
            joined_at=m.joined_at,
            is_admin=m.role.is_admin if m.role else False,
        )
        for m in team.members
    ]

    return TeamWithMembers(
        id=team.id,
        name=team.name,
        slug=team.slug,
        description=team.description,
        parent_team_id=team.parent_team_id,
        owner_id=team.owner_id,
        created_at=team.created_at,
        updated_at=team.updated_at,
        owner=UserBrief(
            id=team.owner.id,
            email=team.owner.email,
            first_name=team.owner.first_name,
            last_name=team.owner.last_name,
        ),
        members=members,
        member_count=len(members),
    )


@router.patch("/{slug}", response_model=TeamResponse)
async def update_team(
    slug: str,
    data: TeamUpdate,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
):
    """
    Update team details.

    Only team admins can update.
    """
    team = await team_service.get_team_by_slug(slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    team = await team_service.update_team(team, data)
    return TeamResponse.model_validate(team)


@router.delete("/{slug}")
async def delete_team(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
):
    """
    Delete a team.

    Only team owner or system owner can delete.
    Team must have no sub-teams, no members (except owner), and no roles.
    """
    team = await team_service.get_team_by_slug(slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check permissions
    if not current_user.is_system_owner and team.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owner can delete the team",
        )

    # Check for sub-teams
    sub_teams = await team_service.get_sub_teams(team.id)
    if sub_teams:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete team: has {len(sub_teams)} sub-team(s). Delete sub-teams first.",
        )

    # Check for members (except owner)
    members = await team_service.get_team_members(team.id)
    non_owner_members = [m for m in members if m.user_id != team.owner_id]
    if non_owner_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete team: has {len(non_owner_members)} member(s). Remove members first.",
        )

    # Check for roles
    roles = await team_service.get_team_roles(team.id)
    if roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete team: has {len(roles)} role(s). Delete roles first.",
        )

    await team_service.delete_team(team)
    return {"message": "Team deleted"}


@router.get("/{slug}/sub-teams", response_model=List[TeamBrief])
async def get_sub_teams(
    slug: str,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
):
    """
    Get direct sub-teams of a team.
    """
    team = await team_service.get_team_by_slug(slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    sub_teams = await team_service.get_sub_teams(team.id)

    return [
        TeamBrief(id=t.id, name=t.name, slug=t.slug)
        for t in sub_teams
    ]


@router.post("/{slug}/members/{user_id}")
async def add_team_member(
    request: Request,
    slug: str,
    user_id: UUID,
    role_id: Optional[UUID] = None,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """
    Add a user to a team.
    """
    team = await team_service.get_team_by_slug(slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check if already a member
    existing = await team_service.get_team_member(team.id, user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this team",
        )

    # Validate role
    if role_id:
        role = await team_service.get_role_by_id(role_id)
        if not role or role.team_id != team.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role for this team",
            )

    member = await team_service.add_team_member(team.id, user_id, role_id)

    # Log activity
    await activity_service.log_member_added(
        actor_id=current_user.id,
        team_id=team.id,
        user_id=user_id,
        user_email="",  # TODO: Get user email
        role_name=member.role.name if member.role else None,
        ip_address=get_client_ip(request),
    )

    return {"message": "Member added"}


@router.delete("/{slug}/members/{user_id}")
async def remove_team_member(
    slug: str,
    user_id: UUID,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
):
    """
    Remove a user from a team.
    """
    team = await team_service.get_team_by_slug(slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    member = await team_service.get_team_member(team.id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this team",
        )

    # Prevent removing team owner
    if team.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove team owner",
        )

    await team_service.remove_team_member(member)
    return {"message": "Member removed"}


@router.patch("/{slug}/members/{user_id}/role")
async def update_member_role(
    slug: str,
    user_id: UUID,
    role_id: Optional[UUID] = None,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
):
    """
    Update a member's role in a team.
    """
    team = await team_service.get_team_by_slug(slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    member = await team_service.get_team_member(team.id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this team",
        )

    # Validate role
    if role_id:
        role = await team_service.get_role_by_id(role_id)
        if not role or role.team_id != team.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role for this team",
            )

    await team_service.update_member_role(member, role_id)
    return {"message": "Role updated"}
