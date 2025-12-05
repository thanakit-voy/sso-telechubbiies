"""
ActivityLog model for audit trail.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.team import Team


class ActivityLog(Base):
    """
    Activity log model for audit trail.

    Records all important actions in the system for security
    and compliance purposes.
    """

    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    actor_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    extra_data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    actor: Mapped["User"] = relationship(
        "User",
        back_populates="activity_logs",
    )
    actor_team: Mapped[Optional["Team"]] = relationship(
        "Team",
        back_populates="activity_logs",
    )

    def __repr__(self) -> str:
        return f"<ActivityLog {self.action} by {self.actor_id}>"


# Common action types
class ActivityAction:
    """Constants for activity log actions."""

    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"

    # User
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"

    # Team
    TEAM_CREATED = "team_created"
    TEAM_UPDATED = "team_updated"
    TEAM_DELETED = "team_deleted"

    # Role
    ROLE_CREATED = "role_created"
    ROLE_UPDATED = "role_updated"
    ROLE_DELETED = "role_deleted"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_UNASSIGNED = "role_unassigned"

    # Workspace
    WORKSPACE_CREATED = "workspace_created"
    WORKSPACE_UPDATED = "workspace_updated"
    WORKSPACE_DELETED = "workspace_deleted"
    WORKSPACE_GRANTED_TO_TEAM = "workspace_granted_to_team"
    WORKSPACE_REVOKED_FROM_TEAM = "workspace_revoked_from_team"
    WORKSPACE_GRANTED_TO_USER = "workspace_granted_to_user"
    WORKSPACE_REVOKED_FROM_USER = "workspace_revoked_from_user"

    # Permission
    PERMISSION_CREATED = "permission_created"
    PERMISSION_UPDATED = "permission_updated"
    PERMISSION_DELETED = "permission_deleted"
    PERMISSION_GRANTED_TO_TEAM = "permission_granted_to_team"
    PERMISSION_REVOKED_FROM_TEAM = "permission_revoked_from_team"
    PERMISSION_GRANTED_TO_ROLE = "permission_granted_to_role"
    PERMISSION_REVOKED_FROM_ROLE = "permission_revoked_from_role"

    # Invitation
    INVITATION_CREATED = "invitation_created"
    INVITATION_ACCEPTED = "invitation_accepted"
    INVITATION_CANCELLED = "invitation_cancelled"

    # Member
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"

    # OAuth Client
    OAUTH_CLIENT_CREATED = "oauth_client_created"
    OAUTH_CLIENT_UPDATED = "oauth_client_updated"
    OAUTH_CLIENT_DELETED = "oauth_client_deleted"
    OAUTH_CLIENT_SECRET_ROTATED = "oauth_client_secret_rotated"


class ResourceType:
    """Constants for resource types."""
    USER = "user"
    TEAM = "team"
    ROLE = "role"
    WORKSPACE = "workspace"
    PERMISSION = "permission"
    INVITATION = "invitation"
    OAUTH_CLIENT = "oauth_client"
    SESSION = "session"
