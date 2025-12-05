"""
Permission management endpoints.
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
from app.schemas.permission import (
    PermissionCreate,
    PermissionUpdate,
    PermissionResponse,
    PermissionBrief,
    PermissionGrantToTeam,
)

router = APIRouter()


@router.get("", response_model=List[PermissionResponse])
async def list_permissions(
    current_user: User = Depends(get_current_system_owner),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    List all global permissions.

    Only system owner can list all permissions.
    """
    permissions = await permission_service.get_global_permissions()
    return [
        PermissionResponse(
            id=p.id,
            name=p.name,
            slug=p.slug,
            description=p.description,
            team_id=p.team_id,
            is_global=p.is_global,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in permissions
    ]


@router.post("", response_model=PermissionResponse)
async def create_permission(
    data: PermissionCreate,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    Create a new permission.

    System owner can create global permissions (team_id=null).
    Team admins can create team-specific permissions.
    """
    # Check slug uniqueness
    if await permission_service.permission_slug_exists(data.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission slug already exists",
        )

    # Check permissions
    if data.team_id:
        # Creating team-specific permission
        if not current_user.is_system_owner:
            is_admin = await team_service.is_team_admin(data.team_id, current_user.id)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required to create team permissions",
                )
    else:
        # Creating global permission
        if not current_user.is_system_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system owner can create global permissions",
            )

    permission = await permission_service.create_permission(
        name=data.name,
        slug=data.slug,
        description=data.description,
        team_id=data.team_id,
    )

    return PermissionResponse(
        id=permission.id,
        name=permission.name,
        slug=permission.slug,
        description=permission.description,
        team_id=permission.team_id,
        is_global=permission.is_global,
        created_at=permission.created_at,
        updated_at=permission.updated_at,
    )


@router.get("/{slug}", response_model=PermissionResponse)
async def get_permission(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    Get permission details.
    """
    permission = await permission_service.get_permission_by_slug(slug)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    return PermissionResponse(
        id=permission.id,
        name=permission.name,
        slug=permission.slug,
        description=permission.description,
        team_id=permission.team_id,
        is_global=permission.is_global,
        created_at=permission.created_at,
        updated_at=permission.updated_at,
    )


@router.patch("/{slug}", response_model=PermissionResponse)
async def update_permission(
    slug: str,
    data: PermissionUpdate,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    Update permission details.
    """
    permission = await permission_service.get_permission_by_slug(slug)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    # Check permissions
    if permission.team_id:
        if not current_user.is_system_owner:
            is_admin = await team_service.is_team_admin(
                permission.team_id, current_user.id
            )
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required",
                )
    else:
        if not current_user.is_system_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system owner can update global permissions",
            )

    permission = await permission_service.update_permission(permission, data)

    return PermissionResponse(
        id=permission.id,
        name=permission.name,
        slug=permission.slug,
        description=permission.description,
        team_id=permission.team_id,
        is_global=permission.is_global,
        created_at=permission.created_at,
        updated_at=permission.updated_at,
    )


@router.delete("/{slug}")
async def delete_permission(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    Delete a permission.

    Permission must not be assigned to any roles or granted to any teams.
    """
    permission = await permission_service.get_permission_by_slug(slug)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    # Check permissions
    if permission.team_id:
        if not current_user.is_system_owner:
            is_admin = await team_service.is_team_admin(
                permission.team_id, current_user.id
            )
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required",
                )
    else:
        if not current_user.is_system_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system owner can delete global permissions",
            )

    # Check for roles using this permission
    roles_with_permission = await permission_service.get_roles_with_permission(permission.id)
    if roles_with_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete permission: assigned to {len(roles_with_permission)} role(s). Remove from roles first.",
        )

    # Check for teams with this permission granted
    teams_with_permission = await permission_service.get_teams_with_permission(permission.id)
    if teams_with_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete permission: granted to {len(teams_with_permission)} team(s). Revoke access first.",
        )

    await permission_service.delete_permission(permission)
    return {"message": "Permission deleted"}


@router.post("/teams/{team_slug}/permissions")
async def grant_permissions_to_team(
    request: Request,
    team_slug: str,
    data: PermissionGrantToTeam,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """
    Grant permission access to a team.

    System owner can grant any global permission.
    Team admins can only grant permissions they have access to.
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
                detail="Only system owner can grant to root teams",
            )

    for permission_id in data.permission_ids:
        permission = await permission_service.get_permission_by_id(permission_id)
        if not permission:
            continue

        # Check if granter has access (for non-owners)
        if not current_user.is_system_owner:
            if permission.is_global:
                # Need parent to have access to global permission
                parent_has_access = await permission_service.team_has_permission_access(
                    team.parent_team_id, permission_id
                )
                if not parent_has_access:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot grant permission {permission.slug} - no access",
                    )

        # Check if already granted
        already_granted = await permission_service.team_has_permission_access(
            team.id, permission_id
        )
        if not already_granted:
            await team_service.grant_permission_to_team(
                team_id=team.id,
                permission_id=permission_id,
                granted_by=current_user.id,
            )

    return {"message": "Permissions granted"}


@router.get("/teams/{team_slug}/permissions", response_model=List[PermissionBrief])
async def get_team_permissions(
    team_slug: str,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
):
    """
    Get permissions granted to a team.
    """
    team = await team_service.get_team_by_slug(team_slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    team_permissions = await team_service.get_team_permissions(team.id)

    return [
        PermissionBrief(
            id=tp.permission.id,
            name=tp.permission.name,
            slug=tp.permission.slug,
        )
        for tp in team_permissions
    ]


@router.delete("/teams/{team_slug}/permissions/{permission_id}")
async def revoke_permission_from_team(
    team_slug: str,
    permission_id: UUID,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    Revoke permission access from a team.
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

    await team_service.revoke_permission_from_team(team.id, permission_id)
    return {"message": "Permission revoked"}
