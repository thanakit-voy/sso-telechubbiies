"""
TeamPermission model for team permission access.
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
    from app.models.permission import Permission
    from app.models.user import User


class TeamPermission(Base):
    """
    Team permission access model.

    Grants permission access to a team (from owner or parent team admin).
    Team admins can then assign these permissions to roles in their team.
    """

    __tablename__ = "team_permissions"
    __table_args__ = (
        UniqueConstraint("team_id", "permission_id", name="uq_team_permissions"),
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
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
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
        back_populates="team_permissions",
    )
    permission: Mapped["Permission"] = relationship(
        "Permission",
        back_populates="team_permissions",
    )
    granter: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<TeamPermission team={self.team_id} permission={self.permission_id}>"
