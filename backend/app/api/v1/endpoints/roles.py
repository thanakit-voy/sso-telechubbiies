"""
Role management endpoints.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_team_service,
    get_permission_service,
    get_current_active_user,
    require_team_admin,
)
from app.models.user import User
from app.services.team_service import TeamService
from app.services.permission_service import PermissionService
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleWithPermissions,
    RolePermissionAssign,
    RolePriorityReorder,
    RoleWithMemberCount,
    PermissionBrief,
)

router = APIRouter()


@router.get("", response_model=List[RoleResponse])
async def list_all_roles(
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
):
    """
    List all roles the user has access to.
    System owner sees all roles, others see roles from their teams.
    Roles are sorted by priority (highest first).
    """
    roles = await team_service.get_accessible_roles(current_user)
    # Sort by priority (descending)
    roles_sorted = sorted(roles, key=lambda r: r.priority, reverse=True)
    return [
        RoleResponse(
            id=r.id,
            name=r.name,
            slug=r.slug,
            description=r.description,
            team_id=r.team_id,
            team_name=r.team.name if r.team else None,
            team_slug=r.team.slug if r.team else None,
            is_admin=r.is_admin,
            priority=r.priority,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in roles_sorted
    ]


@router.get("/teams/{team_slug}/roles", response_model=List[RoleResponse])
async def list_team_roles(
    team_slug: str,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
):
    """
    List all roles for a team.
    Roles are sorted by priority (highest first).
    """
    team = await team_service.get_team_by_slug(team_slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    roles = await team_service.get_team_roles(team.id)
    # Sort by priority (descending)
    roles_sorted = sorted(roles, key=lambda r: r.priority, reverse=True)
    return [RoleResponse.model_validate(r) for r in roles_sorted]


@router.post("/teams/{team_slug}/roles", response_model=RoleResponse)
async def create_role(
    team_slug: str,
    data: RoleCreate,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
):
    """
    Create a new role for a team.

    The first role created for a team will automatically be an admin role with priority 100.
    Subsequent roles will have decreasing priority (99, 98, ...) and will not be admin roles.
    """
    team = await team_service.get_team_by_slug(team_slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check slug uniqueness
    if await team_service.role_slug_exists(data.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role slug already exists",
        )

    # Get existing roles to determine priority and is_admin
    existing_roles = await team_service.get_team_roles(team.id)

    if len(existing_roles) == 0:
        # First role is always admin with priority 100
        is_admin = True
        priority = 100
    else:
        # Subsequent roles are not admin, priority decreases by 1
        is_admin = False
        # Find the lowest priority and subtract 1
        min_priority = min(r.priority for r in existing_roles)
        priority = max(min_priority - 1, 0)

    role = await team_service.create_role(
        team_id=team.id,
        name=data.name,
        slug=data.slug,
        description=data.description,
        is_admin=is_admin,
        priority=priority,
    )

    return RoleResponse.model_validate(role)


@router.get("/{slug}", response_model=RoleWithPermissions)
async def get_role(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    Get role details with permissions.
    """
    role = await team_service.get_role_by_slug(slug)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Check access
    if not current_user.is_system_owner:
        member = await team_service.get_team_member(role.team_id, current_user.id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this team",
            )

    permissions = await permission_service.get_role_permissions(role.id)

    return RoleWithPermissions(
        id=role.id,
        name=role.name,
        slug=role.slug,
        description=role.description,
        team_id=role.team_id,
        is_admin=role.is_admin,
        created_at=role.created_at,
        updated_at=role.updated_at,
        permissions=[
            PermissionBrief(id=p.id, name=p.name, slug=p.slug)
            for p in permissions
        ],
    )


@router.patch("/{slug}", response_model=RoleResponse)
async def update_role(
    slug: str,
    data: RoleUpdate,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
):
    """
    Update role details.

    Priority can only be changed if no members are using this role.
    """
    role = await team_service.get_role_by_slug(slug)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Check admin access
    if not current_user.is_system_owner:
        is_admin = await team_service.is_team_admin(role.team_id, current_user.id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

    # Check if priority is being changed and there are members using this role
    if data.priority is not None and data.priority != role.priority:
        members_with_role = await team_service.get_members_with_role(role.id)
        if members_with_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot change priority: {len(members_with_role)} member(s) are using this role. Reassign their role first.",
            )

    role = await team_service.update_role(role, data)
    return RoleResponse.model_validate(role)


@router.delete("/{slug}")
async def delete_role(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
):
    """
    Delete a role.

    Role must not be assigned to any team members.
    """
    role = await team_service.get_role_by_slug(slug)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Check admin access
    if not current_user.is_system_owner:
        is_admin = await team_service.is_team_admin(role.team_id, current_user.id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

    # Check for members using this role
    members_with_role = await team_service.get_members_with_role(role.id)
    if members_with_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role: {len(members_with_role)} member(s) are using this role. Reassign or remove their role first.",
        )

    await team_service.delete_role(role)
    return {"message": "Role deleted"}


@router.post("/{slug}/permissions", response_model=RoleWithPermissions)
async def assign_permissions_to_role(
    slug: str,
    data: RolePermissionAssign,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """
    Assign permissions to a role.

    Replaces existing permissions with the provided list.
    """
    role = await team_service.get_role_by_slug(slug)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Check admin access
    if not current_user.is_system_owner:
        is_admin = await team_service.is_team_admin(role.team_id, current_user.id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

    # Validate permissions and check team access
    team_permissions = await team_service.get_team_permissions(role.team_id)
    available_permission_ids = {tp.permission_id for tp in team_permissions}

    # Also include team-created permissions
    team_created = await permission_service.get_team_created_permissions(role.team_id)
    for p in team_created:
        available_permission_ids.add(p.id)

    # For system owner, include global permissions
    if current_user.is_system_owner:
        global_permissions = await permission_service.get_global_permissions()
        for p in global_permissions:
            available_permission_ids.add(p.id)

    # Validate all requested permissions are available
    for perm_id in data.permission_ids:
        if perm_id not in available_permission_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission {perm_id} is not available for this team",
            )

    # Get current permissions
    current_permissions = await permission_service.get_role_permissions(role.id)
    current_perm_ids = {p.id for p in current_permissions}

    # Remove permissions not in new list
    for perm in current_permissions:
        if perm.id not in data.permission_ids:
            await permission_service.revoke_permission_from_role(role.id, perm.id)

    # Add new permissions
    for perm_id in data.permission_ids:
        if perm_id not in current_perm_ids:
            await permission_service.assign_permission_to_role(role.id, perm_id)

    # Return updated role
    updated_permissions = await permission_service.get_role_permissions(role.id)

    return RoleWithPermissions(
        id=role.id,
        name=role.name,
        slug=role.slug,
        description=role.description,
        team_id=role.team_id,
        is_admin=role.is_admin,
        created_at=role.created_at,
        updated_at=role.updated_at,
        permissions=[
            PermissionBrief(id=p.id, name=p.name, slug=p.slug)
            for p in updated_permissions
        ],
    )


@router.get("/teams/{team_slug}/roles/with-members", response_model=List[RoleWithMemberCount])
async def list_team_roles_with_member_count(
    team_slug: str,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
):
    """
    List all roles for a team with member counts.
    Used for priority reordering - roles with members cannot be reordered.
    """
    team = await team_service.get_team_by_slug(team_slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    roles = await team_service.get_team_roles(team.id)
    # Sort by priority (descending)
    roles_sorted = sorted(roles, key=lambda r: r.priority, reverse=True)

    result = []
    for r in roles_sorted:
        members = await team_service.get_members_with_role(r.id)
        result.append(
            RoleWithMemberCount(
                id=r.id,
                name=r.name,
                slug=r.slug,
                description=r.description,
                team_id=r.team_id,
                team_name=team.name,
                team_slug=team.slug,
                is_admin=r.is_admin,
                priority=r.priority,
                created_at=r.created_at,
                updated_at=r.updated_at,
                member_count=len(members),
            )
        )

    return result


@router.post("/teams/{team_slug}/roles/reorder", response_model=List[RoleResponse])
async def reorder_team_roles(
    team_slug: str,
    data: RolePriorityReorder,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
):
    """
    Reorder role priorities for a team.

    - Roles with members cannot be reordered (will return error)
    - Admin roles cannot be reordered
    - Role IDs should be in order from highest priority to lowest
    """
    team = await team_service.get_team_by_slug(team_slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    roles = await team_service.get_team_roles(team.id)
    role_map = {r.id: r for r in roles}

    # Validate all role_ids belong to this team
    for role_id in data.role_ids:
        if role_id not in role_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role {role_id} not found in this team",
            )

    # Check that roles with members are not being reordered
    for role_id in data.role_ids:
        role = role_map[role_id]

        # Admin roles cannot be reordered
        if role.is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Admin role '{role.name}' cannot be reordered",
            )

        # Roles with members cannot be reordered
        members = await team_service.get_members_with_role(role_id)
        if members:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role.name}' has {len(members)} member(s) and cannot be reordered",
            )

    # Find the admin role to preserve its priority
    admin_roles = [r for r in roles if r.is_admin]
    non_admin_roles = [r for r in roles if not r.is_admin]

    # Assign new priorities (admin stays at top)
    # Non-admin roles start from 99 and decrease
    priority = 99
    for role_id in data.role_ids:
        role = role_map[role_id]
        if not role.is_admin:
            role.priority = priority
            priority -= 1

    await team_service.db.commit()

    # Reload and return updated roles
    roles = await team_service.get_team_roles(team.id)
    roles_sorted = sorted(roles, key=lambda r: r.priority, reverse=True)
    return [RoleResponse.model_validate(r) for r in roles_sorted]
