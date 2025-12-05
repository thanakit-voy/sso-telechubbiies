"""
Team service for team management operations.
"""

import uuid
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.team import Team
from app.models.role import Role
from app.models.team_member import TeamMember
from app.models.team_workspace import TeamWorkspace
from app.models.team_permission import TeamPermission
from app.models.user import User
from app.schemas.team import TeamCreate, TeamUpdate
from app.schemas.role import RoleCreate, RoleUpdate


class TeamService:
    """Service for team management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Team Operations ====================

    async def get_team_by_id(self, team_id: uuid.UUID) -> Optional[Team]:
        """Get team by ID."""
        result = await self.db.execute(
            select(Team).where(Team.id == team_id)
        )
        return result.scalar_one_or_none()

    async def get_team_by_slug(self, slug: str) -> Optional[Team]:
        """Get team by slug."""
        result = await self.db.execute(
            select(Team).where(Team.slug == slug.lower())
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        """Check if slug already exists."""
        result = await self.db.execute(
            select(Team.id).where(Team.slug == slug.lower())
        )
        return result.scalar_one_or_none() is not None

    async def create_team(
        self,
        name: str,
        slug: str,
        owner_id: uuid.UUID,
        description: Optional[str] = None,
        parent_team_id: Optional[uuid.UUID] = None,
    ) -> Team:
        """Create a new team."""
        team = Team(
            name=name,
            slug=slug.lower(),
            description=description,
            owner_id=owner_id,
            parent_team_id=parent_team_id,
        )
        self.db.add(team)
        await self.db.commit()
        await self.db.refresh(team)
        return team

    async def update_team(
        self,
        team: Team,
        update_data: TeamUpdate,
    ) -> Team:
        """Update team."""
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(team, field, value)

        await self.db.commit()
        await self.db.refresh(team)
        return team

    async def delete_team(self, team: Team) -> None:
        """Delete team and all sub-teams."""
        await self.db.delete(team)
        await self.db.commit()

    async def get_team_with_members(self, team_id: uuid.UUID) -> Optional[Team]:
        """Get team with members loaded."""
        result = await self.db.execute(
            select(Team)
            .options(
                selectinload(Team.members).selectinload(TeamMember.user),
                selectinload(Team.members).selectinload(TeamMember.role),
                selectinload(Team.owner),
            )
            .where(Team.id == team_id)
        )
        return result.scalar_one_or_none()

    async def get_sub_teams(self, team_id: uuid.UUID) -> List[Team]:
        """Get direct sub-teams of a team."""
        result = await self.db.execute(
            select(Team).where(Team.parent_team_id == team_id)
        )
        return list(result.scalars().all())

    async def get_user_teams(self, user_id: uuid.UUID) -> List[Team]:
        """Get all teams a user is a member of."""
        result = await self.db.execute(
            select(Team)
            .join(TeamMember, Team.id == TeamMember.team_id)
            .where(TeamMember.user_id == user_id)
        )
        return list(result.scalars().all())

    # ==================== Role Operations ====================

    async def get_role_by_id(self, role_id: uuid.UUID) -> Optional[Role]:
        """Get role by ID."""
        result = await self.db.execute(
            select(Role).where(Role.id == role_id)
        )
        return result.scalar_one_or_none()

    async def get_role_by_slug(self, slug: str) -> Optional[Role]:
        """Get role by slug."""
        result = await self.db.execute(
            select(Role).where(Role.slug == slug.lower())
        )
        return result.scalar_one_or_none()

    async def role_slug_exists(self, slug: str) -> bool:
        """Check if role slug already exists."""
        result = await self.db.execute(
            select(Role.id).where(Role.slug == slug.lower())
        )
        return result.scalar_one_or_none() is not None

    async def get_team_roles(self, team_id: uuid.UUID) -> List[Role]:
        """Get all roles for a team."""
        result = await self.db.execute(
            select(Role).where(Role.team_id == team_id)
        )
        return list(result.scalars().all())

    async def get_accessible_roles(self, user: User) -> List[Role]:
        """Get all roles the user has access to."""
        if user.is_system_owner:
            # System owner sees all roles
            result = await self.db.execute(
                select(Role).options(selectinload(Role.team))
            )
            return list(result.scalars().all())
        else:
            # Regular users see roles from their teams
            result = await self.db.execute(
                select(Role)
                .join(Team, Role.team_id == Team.id)
                .join(TeamMember, Team.id == TeamMember.team_id)
                .where(TeamMember.user_id == user.id)
                .options(selectinload(Role.team))
            )
            return list(result.scalars().all())

    async def create_role(
        self,
        team_id: uuid.UUID,
        name: str,
        slug: str,
        description: Optional[str] = None,
        is_admin: bool = False,
        priority: int = 0,
    ) -> Role:
        """Create a new role for a team."""
        role = Role(
            team_id=team_id,
            name=name,
            slug=slug.lower(),
            description=description,
            is_admin=is_admin,
            priority=priority,
        )
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def update_role(
        self,
        role: Role,
        update_data: RoleUpdate,
    ) -> Role:
        """Update role."""
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(role, field, value)

        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def delete_role(self, role: Role) -> None:
        """Delete role."""
        await self.db.delete(role)
        await self.db.commit()

    # ==================== Member Operations ====================

    async def get_team_member(
        self,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[TeamMember]:
        """Get team membership for a user."""
        result = await self.db.execute(
            select(TeamMember)
            .options(
                selectinload(TeamMember.role),
                selectinload(TeamMember.user),
            )
            .where(
                and_(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def add_team_member(
        self,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        role_id: Optional[uuid.UUID] = None,
    ) -> TeamMember:
        """Add a user to a team."""
        member = TeamMember(
            team_id=team_id,
            user_id=user_id,
            role_id=role_id,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def update_member_role(
        self,
        member: TeamMember,
        role_id: Optional[uuid.UUID],
    ) -> TeamMember:
        """Update member's role in a team."""
        member.role_id = role_id
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_team_member(self, member: TeamMember) -> None:
        """Remove a user from a team."""
        await self.db.delete(member)
        await self.db.commit()

    async def is_team_admin(
        self,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Check if user is an admin of the team."""
        member = await self.get_team_member(team_id, user_id)
        if not member:
            return False
        return member.role is not None and member.role.is_admin

    async def get_team_members(self, team_id: uuid.UUID) -> List[TeamMember]:
        """Get all members of a team."""
        result = await self.db.execute(
            select(TeamMember)
            .options(
                selectinload(TeamMember.user),
                selectinload(TeamMember.role),
            )
            .where(TeamMember.team_id == team_id)
        )
        return list(result.scalars().all())

    async def get_members_with_role(self, role_id: uuid.UUID) -> List[TeamMember]:
        """Get all members that have a specific role assigned."""
        result = await self.db.execute(
            select(TeamMember)
            .options(selectinload(TeamMember.user))
            .where(TeamMember.role_id == role_id)
        )
        return list(result.scalars().all())

    # ==================== Workspace Access ====================

    async def get_team_workspaces(self, team_id: uuid.UUID) -> List[TeamWorkspace]:
        """Get all workspaces granted to a team."""
        result = await self.db.execute(
            select(TeamWorkspace)
            .options(selectinload(TeamWorkspace.workspace))
            .where(TeamWorkspace.team_id == team_id)
        )
        return list(result.scalars().all())

    async def grant_workspace_to_team(
        self,
        team_id: uuid.UUID,
        workspace_id: uuid.UUID,
        granted_by: uuid.UUID,
    ) -> TeamWorkspace:
        """Grant workspace access to a team."""
        team_workspace = TeamWorkspace(
            team_id=team_id,
            workspace_id=workspace_id,
            granted_by=granted_by,
        )
        self.db.add(team_workspace)
        await self.db.commit()
        await self.db.refresh(team_workspace)
        return team_workspace

    async def revoke_workspace_from_team(
        self,
        team_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        """Revoke workspace access from a team."""
        result = await self.db.execute(
            select(TeamWorkspace).where(
                and_(
                    TeamWorkspace.team_id == team_id,
                    TeamWorkspace.workspace_id == workspace_id,
                )
            )
        )
        team_workspace = result.scalar_one_or_none()
        if team_workspace:
            await self.db.delete(team_workspace)
            await self.db.commit()

    # ==================== Permission Access ====================

    async def get_team_permissions(self, team_id: uuid.UUID) -> List[TeamPermission]:
        """Get all permissions granted to a team."""
        result = await self.db.execute(
            select(TeamPermission)
            .options(selectinload(TeamPermission.permission))
            .where(TeamPermission.team_id == team_id)
        )
        return list(result.scalars().all())

    async def grant_permission_to_team(
        self,
        team_id: uuid.UUID,
        permission_id: uuid.UUID,
        granted_by: uuid.UUID,
    ) -> TeamPermission:
        """Grant permission access to a team."""
        team_permission = TeamPermission(
            team_id=team_id,
            permission_id=permission_id,
            granted_by=granted_by,
        )
        self.db.add(team_permission)
        await self.db.commit()
        await self.db.refresh(team_permission)
        return team_permission

    async def revoke_permission_from_team(
        self,
        team_id: uuid.UUID,
        permission_id: uuid.UUID,
    ) -> None:
        """Revoke permission access from a team."""
        result = await self.db.execute(
            select(TeamPermission).where(
                and_(
                    TeamPermission.team_id == team_id,
                    TeamPermission.permission_id == permission_id,
                )
            )
        )
        team_permission = result.scalar_one_or_none()
        if team_permission:
            await self.db.delete(team_permission)
            await self.db.commit()

    # ==================== Hierarchy Helpers ====================

    async def get_parent_chain(self, team: Team) -> List[Team]:
        """Get all parent teams up to root."""
        parents = []
        current = team

        while current.parent_team_id:
            parent = await self.get_team_by_id(current.parent_team_id)
            if parent:
                parents.append(parent)
                current = parent
            else:
                break

        return parents

    async def is_descendant_of(
        self,
        team: Team,
        potential_ancestor_id: uuid.UUID,
    ) -> bool:
        """Check if team is a descendant of another team."""
        parents = await self.get_parent_chain(team)
        return any(p.id == potential_ancestor_id for p in parents)
