"""
Team model for hierarchical team/organization structure.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.role import Role
    from app.models.team_member import TeamMember
    from app.models.team_workspace import TeamWorkspace
    from app.models.team_permission import TeamPermission
    from app.models.invitation import Invitation
    from app.models.activity_log import ActivityLog


class Team(Base):
    """
    Team/Organization model with hierarchical structure.

    Teams can have sub-teams (unlimited depth) and inherit
    workspaces/permissions from parent teams.
    """

    __tablename__ = "teams"
    __table_args__ = (
        CheckConstraint(
            r"slug ~ '^[a-zA-Z0-9_]+$'",
            name="teams_slug_format",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_teams",
        foreign_keys=[owner_id],
    )
    parent_team: Mapped[Optional["Team"]] = relationship(
        "Team",
        remote_side="Team.id",
        back_populates="sub_teams",
        foreign_keys=[parent_team_id],
    )
    sub_teams: Mapped[List["Team"]] = relationship(
        "Team",
        back_populates="parent_team",
        foreign_keys="Team.parent_team_id",
        cascade="all, delete-orphan",
    )
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        back_populates="team",
        cascade="all, delete-orphan",
    )
    members: Mapped[List["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="team",
        cascade="all, delete-orphan",
    )
    team_workspaces: Mapped[List["TeamWorkspace"]] = relationship(
        "TeamWorkspace",
        back_populates="team",
        cascade="all, delete-orphan",
    )
    team_permissions: Mapped[List["TeamPermission"]] = relationship(
        "TeamPermission",
        back_populates="team",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[List["Invitation"]] = relationship(
        "Invitation",
        back_populates="team",
        cascade="all, delete-orphan",
    )
    activity_logs: Mapped[List["ActivityLog"]] = relationship(
        "ActivityLog",
        back_populates="actor_team",
    )

    @property
    def is_root_team(self) -> bool:
        """Check if this is a root (top-level) team."""
        return self.parent_team_id is None

    def __repr__(self) -> str:
        return f"<Team {self.slug}>"
