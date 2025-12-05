"""
Permission and Workspace service for access control.
"""

import uuid
from typing import List, Optional, Set

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.permission import Permission
from app.models.workspace import Workspace
from app.models.role_permission import RolePermission
from app.models.team_permission import TeamPermission
from app.models.team_workspace import TeamWorkspace
from app.models.user_workspace import UserWorkspace
from app.models.team_member import TeamMember
from app.models.team import Team
from app.schemas.permission import PermissionCreate, PermissionUpdate
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


class PermissionService:
    """Service for permission and workspace management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Permission Operations ====================

    async def get_permission_by_id(
        self, permission_id: uuid.UUID
    ) -> Optional[Permission]:
        """Get permission by ID."""
        result = await self.db.execute(
            select(Permission).where(Permission.id == permission_id)
        )
        return result.scalar_one_or_none()

    async def get_permission_by_slug(self, slug: str) -> Optional[Permission]:
        """Get permission by slug."""
        result = await self.db.execute(
            select(Permission).where(Permission.slug == slug.lower())
        )
        return result.scalar_one_or_none()

    async def permission_slug_exists(self, slug: str) -> bool:
        """Check if permission slug exists."""
        result = await self.db.execute(
            select(Permission.id).where(Permission.slug == slug.lower())
        )
        return result.scalar_one_or_none() is not None

    async def create_permission(
        self,
        name: str,
        slug: str,
        description: Optional[str] = None,
        team_id: Optional[uuid.UUID] = None,
    ) -> Permission:
        """Create a new permission."""
        permission = Permission(
            name=name,
            slug=slug.lower(),
            description=description,
            team_id=team_id,
        )
        self.db.add(permission)
        await self.db.commit()
        await self.db.refresh(permission)
        return permission

    async def update_permission(
        self,
        permission: Permission,
        update_data: PermissionUpdate,
    ) -> Permission:
        """Update permission."""
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(permission, field, value)
        await self.db.commit()
        await self.db.refresh(permission)
        return permission

    async def delete_permission(self, permission: Permission) -> None:
        """Delete permission."""
        await self.db.delete(permission)
        await self.db.commit()

    async def get_roles_with_permission(self, permission_id: uuid.UUID) -> List[RolePermission]:
        """Get all roles that have a permission assigned."""
        result = await self.db.execute(
            select(RolePermission)
            .options(selectinload(RolePermission.role))
            .where(RolePermission.permission_id == permission_id)
        )
        return list(result.scalars().all())

    async def get_teams_with_permission(self, permission_id: uuid.UUID) -> List[TeamPermission]:
        """Get all teams that have been granted a permission."""
        result = await self.db.execute(
            select(TeamPermission)
            .options(selectinload(TeamPermission.team))
            .where(TeamPermission.permission_id == permission_id)
        )
        return list(result.scalars().all())

    async def get_global_permissions(self) -> List[Permission]:
        """Get all global permissions (created by owner)."""
        result = await self.db.execute(
            select(Permission).where(Permission.team_id.is_(None))
        )
        return list(result.scalars().all())

    async def get_team_created_permissions(
        self, team_id: uuid.UUID
    ) -> List[Permission]:
        """Get permissions created by a specific team."""
        result = await self.db.execute(
            select(Permission).where(Permission.team_id == team_id)
        )
        return list(result.scalars().all())

    # ==================== Role-Permission Operations ====================

    async def assign_permission_to_role(
        self,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
    ) -> RolePermission:
        """Assign a permission to a role."""
        role_permission = RolePermission(
            role_id=role_id,
            permission_id=permission_id,
        )
        self.db.add(role_permission)
        await self.db.commit()
        await self.db.refresh(role_permission)
        return role_permission

    async def revoke_permission_from_role(
        self,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
    ) -> None:
        """Revoke a permission from a role."""
        result = await self.db.execute(
            select(RolePermission).where(
                and_(
                    RolePermission.role_id == role_id,
                    RolePermission.permission_id == permission_id,
                )
            )
        )
        role_permission = result.scalar_one_or_none()
        if role_permission:
            await self.db.delete(role_permission)
            await self.db.commit()

    async def get_role_permissions(self, role_id: uuid.UUID) -> List[Permission]:
        """Get all permissions assigned to a role."""
        result = await self.db.execute(
            select(Permission)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .where(RolePermission.role_id == role_id)
        )
        return list(result.scalars().all())

    # ==================== Workspace Operations ====================

    async def get_workspace_by_id(
        self, workspace_id: uuid.UUID
    ) -> Optional[Workspace]:
        """Get workspace by ID."""
        result = await self.db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def get_workspace_by_slug(self, slug: str) -> Optional[Workspace]:
        """Get workspace by slug."""
        result = await self.db.execute(
            select(Workspace).where(Workspace.slug == slug.lower())
        )
        return result.scalar_one_or_none()

    async def workspace_slug_exists(self, slug: str) -> bool:
        """Check if workspace slug exists."""
        result = await self.db.execute(
            select(Workspace.id).where(Workspace.slug == slug.lower())
        )
        return result.scalar_one_or_none() is not None

    async def create_workspace(
        self,
        name: str,
        slug: str,
        created_by: uuid.UUID,
        description: Optional[str] = None,
    ) -> Workspace:
        """Create a new workspace."""
        workspace = Workspace(
            name=name,
            slug=slug.lower(),
            description=description,
            created_by=created_by,
        )
        self.db.add(workspace)
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def update_workspace(
        self,
        workspace: Workspace,
        update_data: WorkspaceUpdate,
    ) -> Workspace:
        """Update workspace."""
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(workspace, field, value)
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def delete_workspace(self, workspace: Workspace) -> None:
        """Delete workspace."""
        await self.db.delete(workspace)
        await self.db.commit()

    async def get_teams_with_workspace(self, workspace_id: uuid.UUID) -> List[TeamWorkspace]:
        """Get all teams that have been granted a workspace."""
        result = await self.db.execute(
            select(TeamWorkspace)
            .options(selectinload(TeamWorkspace.team))
            .where(TeamWorkspace.workspace_id == workspace_id)
        )
        return list(result.scalars().all())

    async def get_users_with_workspace(self, workspace_id: uuid.UUID) -> List[UserWorkspace]:
        """Get all users that have been granted a workspace."""
        result = await self.db.execute(
            select(UserWorkspace)
            .options(selectinload(UserWorkspace.user))
            .where(UserWorkspace.workspace_id == workspace_id)
        )
        return list(result.scalars().all())

    async def get_all_workspaces(self) -> List[Workspace]:
        """Get all workspaces."""
        result = await self.db.execute(select(Workspace))
        return list(result.scalars().all())

    # ==================== User Workspace Operations ====================

    async def grant_workspace_to_user(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        team_id: uuid.UUID,
        granted_by: uuid.UUID,
    ) -> UserWorkspace:
        """Grant workspace access to a user."""
        user_workspace = UserWorkspace(
            user_id=user_id,
            workspace_id=workspace_id,
            team_id=team_id,
            granted_by=granted_by,
        )
        self.db.add(user_workspace)
        await self.db.commit()
        await self.db.refresh(user_workspace)
        return user_workspace

    async def revoke_workspace_from_user(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        team_id: uuid.UUID,
    ) -> None:
        """Revoke workspace access from a user."""
        result = await self.db.execute(
            select(UserWorkspace).where(
                and_(
                    UserWorkspace.user_id == user_id,
                    UserWorkspace.workspace_id == workspace_id,
                    UserWorkspace.team_id == team_id,
                )
            )
        )
        user_workspace = result.scalar_one_or_none()
        if user_workspace:
            await self.db.delete(user_workspace)
            await self.db.commit()

    async def get_user_workspaces(self, user_id: uuid.UUID) -> List[Workspace]:
        """Get all workspaces a user has access to."""
        result = await self.db.execute(
            select(Workspace)
            .join(UserWorkspace, Workspace.id == UserWorkspace.workspace_id)
            .where(UserWorkspace.user_id == user_id)
        )
        return list(result.scalars().all())

    # ==================== Access Check Operations ====================

    async def get_user_permissions(self, user_id: uuid.UUID) -> Set[str]:
        """Get all permission slugs for a user across all teams."""
        # Get user's team memberships with roles
        result = await self.db.execute(
            select(TeamMember)
            .options(selectinload(TeamMember.role))
            .where(TeamMember.user_id == user_id)
        )
        memberships = result.scalars().all()

        permission_slugs: Set[str] = set()

        for membership in memberships:
            if membership.role_id:
                role_perms = await self.get_role_permissions(membership.role_id)
                for perm in role_perms:
                    permission_slugs.add(perm.slug)

        return permission_slugs

    async def user_has_permission(
        self,
        user_id: uuid.UUID,
        permission_slug: str,
    ) -> bool:
        """Check if user has a specific permission."""
        permissions = await self.get_user_permissions(user_id)
        return permission_slug in permissions

    async def user_has_workspace_access(
        self,
        user_id: uuid.UUID,
        workspace_slug: str,
    ) -> bool:
        """Check if user has access to a workspace."""
        workspace = await self.get_workspace_by_slug(workspace_slug)
        if not workspace:
            return False

        result = await self.db.execute(
            select(UserWorkspace.id).where(
                and_(
                    UserWorkspace.user_id == user_id,
                    UserWorkspace.workspace_id == workspace.id,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def team_has_workspace_access(
        self,
        team_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> bool:
        """Check if team has access to a workspace."""
        result = await self.db.execute(
            select(TeamWorkspace.id).where(
                and_(
                    TeamWorkspace.team_id == team_id,
                    TeamWorkspace.workspace_id == workspace_id,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def team_has_permission_access(
        self,
        team_id: uuid.UUID,
        permission_id: uuid.UUID,
    ) -> bool:
        """Check if team has access to a permission."""
        result = await self.db.execute(
            select(TeamPermission.id).where(
                and_(
                    TeamPermission.team_id == team_id,
                    TeamPermission.permission_id == permission_id,
                )
            )
        )
        return result.scalar_one_or_none() is not None
