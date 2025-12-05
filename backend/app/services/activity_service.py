"""
Activity log service for audit trail.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity_log import ActivityLog, ActivityAction, ResourceType
from app.models.team import Team


class ActivityService:
    """Service for activity logging and retrieval."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        actor_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: Optional[uuid.UUID] = None,
        actor_team_id: Optional[uuid.UUID] = None,
        extra_data: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ActivityLog:
        """Create an activity log entry."""
        log = ActivityLog(
            actor_id=actor_id,
            actor_team_id=actor_team_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            extra_data=extra_data,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_by_id(self, log_id: uuid.UUID) -> Optional[ActivityLog]:
        """Get activity log by ID."""
        result = await self.db.execute(
            select(ActivityLog)
            .options(selectinload(ActivityLog.actor))
            .where(ActivityLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def get_logs(
        self,
        actor_id: Optional[uuid.UUID] = None,
        team_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ActivityLog]:
        """Get activity logs with filters."""
        query = (
            select(ActivityLog)
            .options(selectinload(ActivityLog.actor))
            .order_by(ActivityLog.created_at.desc())
        )

        conditions = []

        if actor_id:
            conditions.append(ActivityLog.actor_id == actor_id)
        if team_id:
            conditions.append(ActivityLog.actor_team_id == team_id)
        if action:
            conditions.append(ActivityLog.action == action)
        if resource_type:
            conditions.append(ActivityLog.resource_type == resource_type)
        if resource_id:
            conditions.append(ActivityLog.resource_id == resource_id)
        if from_date:
            conditions.append(ActivityLog.created_at >= from_date)
        if to_date:
            conditions.append(ActivityLog.created_at <= to_date)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_team_logs(
        self,
        team_id: uuid.UUID,
        include_sub_teams: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ActivityLog]:
        """
        Get activity logs for a team.

        Args:
            team_id: The team ID to get logs for
            include_sub_teams: If True, include logs from direct sub-teams only
            skip: Pagination offset
            limit: Max number of results
        """
        team_ids = [team_id]

        if include_sub_teams:
            # Get direct sub-teams only (not nested)
            result = await self.db.execute(
                select(Team.id).where(Team.parent_team_id == team_id)
            )
            sub_team_ids = result.scalars().all()
            team_ids.extend(sub_team_ids)

        query = (
            select(ActivityLog)
            .options(selectinload(ActivityLog.actor))
            .where(ActivityLog.actor_team_id.in_(team_ids))
            .order_by(ActivityLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_logs(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ActivityLog]:
        """Get activity logs for a specific user."""
        return await self.get_logs(actor_id=user_id, skip=skip, limit=limit)

    async def count_logs(
        self,
        actor_id: Optional[uuid.UUID] = None,
        team_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> int:
        """Count activity logs with filters."""
        from sqlalchemy import func

        query = select(func.count(ActivityLog.id))

        conditions = []

        if actor_id:
            conditions.append(ActivityLog.actor_id == actor_id)
        if team_id:
            conditions.append(ActivityLog.actor_team_id == team_id)
        if action:
            conditions.append(ActivityLog.action == action)
        if resource_type:
            conditions.append(ActivityLog.resource_type == resource_type)
        if from_date:
            conditions.append(ActivityLog.created_at >= from_date)
        if to_date:
            conditions.append(ActivityLog.created_at <= to_date)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar_one()

    # ==================== Convenience Logging Methods ====================

    async def log_login(
        self,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        oauth_client_id: Optional[uuid.UUID] = None,
        oauth_client_name: Optional[str] = None,
        login_method: str = "direct",
    ) -> ActivityLog:
        """
        Log a successful login.

        Args:
            user_id: The user who logged in
            ip_address: Client IP address
            user_agent: Client user agent
            oauth_client_id: OAuth client ID if login via OAuth
            oauth_client_name: OAuth client name for display
            login_method: "direct" for normal login, "oauth" for OAuth login
        """
        extra_data = {
            "login_method": login_method,
        }
        if oauth_client_id:
            extra_data["oauth_client_id"] = str(oauth_client_id)
        if oauth_client_name:
            extra_data["oauth_client_name"] = oauth_client_name

        return await self.log(
            actor_id=user_id,
            action=ActivityAction.LOGIN,
            resource_type=ResourceType.SESSION,
            extra_data=extra_data,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_login_failed(
        self,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log a failed login attempt (no user ID available)."""
        # We can't log this directly since we need an actor_id
        # Could use a system user or skip logging
        pass

    async def log_logout(
        self,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
        oauth_client_id: Optional[uuid.UUID] = None,
        oauth_client_name: Optional[str] = None,
        logout_method: str = "direct",
    ) -> ActivityLog:
        """
        Log a logout.

        Args:
            user_id: The user who logged out
            ip_address: Client IP address
            oauth_client_id: OAuth client ID if logout via OAuth app
            oauth_client_name: OAuth client name for display
            logout_method: "direct" for normal logout, "oauth" for OAuth logout
        """
        extra_data = {
            "logout_method": logout_method,
        }
        if oauth_client_id:
            extra_data["oauth_client_id"] = str(oauth_client_id)
        if oauth_client_name:
            extra_data["oauth_client_name"] = oauth_client_name

        return await self.log(
            actor_id=user_id,
            action=ActivityAction.LOGOUT,
            resource_type=ResourceType.SESSION,
            extra_data=extra_data,
            ip_address=ip_address,
        )

    async def log_team_created(
        self,
        actor_id: uuid.UUID,
        team_id: uuid.UUID,
        team_name: str,
        actor_team_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> ActivityLog:
        """Log team creation."""
        return await self.log(
            actor_id=actor_id,
            action=ActivityAction.TEAM_CREATED,
            resource_type=ResourceType.TEAM,
            resource_id=team_id,
            actor_team_id=actor_team_id,
            extra_data={"team_name": team_name},
            ip_address=ip_address,
        )

    async def log_member_added(
        self,
        actor_id: uuid.UUID,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        user_email: str,
        role_name: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> ActivityLog:
        """Log member addition to a team."""
        return await self.log(
            actor_id=actor_id,
            action=ActivityAction.MEMBER_ADDED,
            resource_type=ResourceType.TEAM,
            resource_id=team_id,
            actor_team_id=team_id,
            extra_data={
                "user_id": str(user_id),
                "user_email": user_email,
                "role_name": role_name,
            },
            ip_address=ip_address,
        )

    async def log_invitation_created(
        self,
        actor_id: uuid.UUID,
        invitation_id: uuid.UUID,
        email: str,
        team_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> ActivityLog:
        """Log invitation creation."""
        return await self.log(
            actor_id=actor_id,
            action=ActivityAction.INVITATION_CREATED,
            resource_type=ResourceType.INVITATION,
            resource_id=invitation_id,
            actor_team_id=team_id,
            extra_data={"email": email},
            ip_address=ip_address,
        )

    async def log_workspace_granted(
        self,
        actor_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workspace_name: str,
        target_team_id: Optional[uuid.UUID] = None,
        target_user_id: Optional[uuid.UUID] = None,
        actor_team_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> ActivityLog:
        """Log workspace access grant."""
        action = (
            ActivityAction.WORKSPACE_GRANTED_TO_TEAM
            if target_team_id
            else ActivityAction.WORKSPACE_GRANTED_TO_USER
        )
        return await self.log(
            actor_id=actor_id,
            action=action,
            resource_type=ResourceType.WORKSPACE,
            resource_id=workspace_id,
            actor_team_id=actor_team_id,
            extra_data={
                "workspace_name": workspace_name,
                "target_team_id": str(target_team_id) if target_team_id else None,
                "target_user_id": str(target_user_id) if target_user_id else None,
            },
            ip_address=ip_address,
        )

    async def log_permission_changed(
        self,
        actor_id: uuid.UUID,
        permission_id: uuid.UUID,
        permission_name: str,
        action: str,
        target_role_id: Optional[uuid.UUID] = None,
        target_team_id: Optional[uuid.UUID] = None,
        actor_team_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> ActivityLog:
        """Log permission changes."""
        return await self.log(
            actor_id=actor_id,
            action=action,
            resource_type=ResourceType.PERMISSION,
            resource_id=permission_id,
            actor_team_id=actor_team_id,
            extra_data={
                "permission_name": permission_name,
                "target_role_id": str(target_role_id) if target_role_id else None,
                "target_team_id": str(target_team_id) if target_team_id else None,
            },
            ip_address=ip_address,
        )
