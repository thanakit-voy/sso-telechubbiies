"""
TeamMember model for user-team membership.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.team import Team
    from app.models.role import Role


class TeamMember(Base):
    """
    Team membership model linking users to teams with roles.

    A user can be a member of multiple teams with different roles.
    """

    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("user_id", "team_id", name="uq_team_members_user_team"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="team_memberships",
    )
    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="members",
    )
    role: Mapped[Optional["Role"]] = relationship(
        "Role",
        back_populates="team_members",
    )

    @property
    def is_admin(self) -> bool:
        """Check if member has admin role in this team."""
        return self.role is not None and self.role.is_admin

    def __repr__(self) -> str:
        return f"<TeamMember user={self.user_id} team={self.team_id}>"
