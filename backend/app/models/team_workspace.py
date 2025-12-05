"""
TeamWorkspace model for team workspace access.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.workspace import Workspace
    from app.models.user import User


class TeamWorkspace(Base):
    """
    Team workspace access model.

    Grants workspace access to a team (from owner or parent team admin).
    Team admins can then grant this workspace to individual users.
    """

    __tablename__ = "team_workspaces"
    __table_args__ = (
        UniqueConstraint("team_id", "workspace_id", name="uq_team_workspaces"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    granted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="team_workspaces",
    )
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="team_workspaces",
    )
    granter: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<TeamWorkspace team={self.team_id} workspace={self.workspace_id}>"
