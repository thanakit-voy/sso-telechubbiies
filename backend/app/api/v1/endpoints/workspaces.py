"""
Workspace management endpoints.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import (
    get_team_service,
    get_permission_service,
    get_activity_service,
    get_current_active_user,
    get_current_system_owner,
    require_team_admin,
    get_client_ip,
)
from app.models.user import User
from app.services.team_service import TeamService
from app.services.permission_service import PermissionService
from app.services.activity_service import ActivityService
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceBrief,
    WorkspaceGrantToTeam,
    WorkspaceGrantToUser,
    TeamWorkspaceResponse,
    UserWorkspaceResponse,
)
from app.schemas.user import UserBrief

router = APIRouter()


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_system_owner),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    List all workspaces.

    Only system owner can list all workspaces.
    """
    workspaces = await permission_service.get_all_workspaces()
    return [WorkspaceResponse.model_validate(w) for w in workspaces]


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    request: Request,
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_system_owner),
    permission_service: PermissionService = Depends(get_permission_service),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """
    Create a new workspace.

    Only system owner can create workspaces.
    """
    # Check slug uniqueness
    if await permission_service.workspace_slug_exists(data.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace slug already exists",
        )

    workspace = await permission_service.create_workspace(
        name=data.name,
        slug=data.slug,
        description=data.description,
        created_by=current_user.id,
    )

    return WorkspaceResponse.model_validate(workspace)


@router.get("/{slug}", response_model=WorkspaceResponse)
async def get_workspace(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    Get workspace details.
    """
    workspace = await permission_service.get_workspace_by_slug(slug)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check access (system owner or has workspace access)
    if not current_user.is_system_owner:
        has_access = await permission_service.user_has_workspace_access(
            current_user.id, slug
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to this workspace",
            )

    return WorkspaceResponse.model_validate(workspace)


@router.patch("/{slug}", response_model=WorkspaceResponse)
async def update_workspace(
    slug: str,
    data: WorkspaceUpdate,
    current_user: User = Depends(get_current_system_owner),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    Update workspace details.

    Only system owner can update workspaces.
    """
    workspace = await permission_service.get_workspace_by_slug(slug)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    workspace = await permission_service.update_workspace(workspace, data)
    return WorkspaceResponse.model_validate(workspace)


@router.delete("/{slug}")
async def delete_workspace(
    slug: str,
    current_user: User = Depends(get_current_system_owner),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    Delete a workspace.

    Only system owner can delete workspaces.
    Workspace must not be granted to any teams or users.
    """
    workspace = await permission_service.get_workspace_by_slug(slug)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check for teams with this workspace
    teams_with_workspace = await permission_service.get_teams_with_workspace(workspace.id)
    if teams_with_workspace:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete workspace: granted to {len(teams_with_workspace)} team(s). Revoke access first.",
        )

    # Check for users with this workspace
    users_with_workspace = await permission_service.get_users_with_workspace(workspace.id)
    if users_with_workspace:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete workspace: granted to {len(users_with_workspace)} user(s). Revoke access first.",
        )

    await permission_service.delete_workspace(workspace)
    return {"message": "Workspace deleted"}


@router.post("/teams/{team_slug}/workspaces")
async def grant_workspaces_to_team(
    request: Request,
    team_slug: str,
    data: WorkspaceGrantToTeam,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """
    Grant workspace access to a team.

    System owner can grant any workspace.
    Team admins can only grant workspaces they have access to.
    """
    team = await team_service.get_team_by_slug(team_slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check permissions
    if not current_user.is_system_owner:
        # Must be admin of parent team
        if team.parent_team_id:
            is_admin = await team_service.is_team_admin(
                team.parent_team_id, current_user.id
            )
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access to parent team required",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system owner can grant to root teams",
            )

    for workspace_id in data.workspace_ids:
        workspace = await permission_service.get_workspace_by_id(workspace_id)
        if not workspace:
            continue

        # Check if granter has access (for non-owners)
        if not current_user.is_system_owner:
            parent_has_access = await permission_service.team_has_workspace_access(
                team.parent_team_id, workspace_id
            )
            if not parent_has_access:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot grant workspace {workspace.slug} - no access",
                )

        # Check if already granted
        already_granted = await permission_service.team_has_workspace_access(
            team.id, workspace_id
        )
        if not already_granted:
            await team_service.grant_workspace_to_team(
                team_id=team.id,
                workspace_id=workspace_id,
                granted_by=current_user.id,
            )

            await activity_service.log_workspace_granted(
                actor_id=current_user.id,
                workspace_id=workspace_id,
                workspace_name=workspace.name,
                target_team_id=team.id,
                ip_address=get_client_ip(request),
            )

    return {"message": "Workspaces granted"}


@router.get("/teams/{team_slug}/workspaces", response_model=List[WorkspaceBrief])
async def get_team_workspaces(
    team_slug: str,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
):
    """
    Get workspaces granted to a team.
    """
    team = await team_service.get_team_by_slug(team_slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    team_workspaces = await team_service.get_team_workspaces(team.id)

    return [
        WorkspaceBrief(
            id=tw.workspace.id,
            name=tw.workspace.name,
            slug=tw.workspace.slug,
        )
        for tw in team_workspaces
    ]


@router.delete("/teams/{team_slug}/workspaces/{workspace_id}")
async def revoke_workspace_from_team(
    team_slug: str,
    workspace_id: UUID,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    Revoke workspace access from a team.
    """
    team = await team_service.get_team_by_slug(team_slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check permissions
    if not current_user.is_system_owner:
        if team.parent_team_id:
            is_admin = await team_service.is_team_admin(
                team.parent_team_id, current_user.id
            )
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access to parent team required",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system owner can revoke from root teams",
            )

    await team_service.revoke_workspace_from_team(team.id, workspace_id)
    return {"message": "Workspace revoked"}


@router.post("/teams/{team_slug}/users/{user_id}/workspaces")
async def grant_workspaces_to_user(
    request: Request,
    team_slug: str,
    user_id: UUID,
    data: WorkspaceGrantToTeam,  # Reuse same schema
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """
    Grant workspace access to a user within a team context.

    Only team admins can grant workspaces that were granted to their team.
    """
    team = await team_service.get_team_by_slug(team_slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check user is member of team
    member = await team_service.get_team_member(team.id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of this team",
        )

    for workspace_id in data.workspace_ids:
        # Check team has access to workspace
        team_has_access = await permission_service.team_has_workspace_access(
            team.id, workspace_id
        )
        if not team_has_access:
            workspace = await permission_service.get_workspace_by_id(workspace_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team doesn't have access to workspace",
            )

        await permission_service.grant_workspace_to_user(
            user_id=user_id,
            workspace_id=workspace_id,
            team_id=team.id,
            granted_by=current_user.id,
        )

    return {"message": "Workspaces granted to user"}


@router.get("/users/me/workspaces", response_model=List[WorkspaceBrief])
async def get_my_workspaces(
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    Get workspaces the current user has access to.
    """
    workspaces = await permission_service.get_user_workspaces(current_user.id)
    return [
        WorkspaceBrief(id=w.id, name=w.name, slug=w.slug)
        for w in workspaces
    ]
