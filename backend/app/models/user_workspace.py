"""
UserWorkspace model for user workspace access.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace
    from app.models.team import Team


class UserWorkspace(Base):
    """
    User workspace access model.

    Grants workspace access to individual users within a team context.
    Only team admins can grant workspaces that were granted to their team.
    """

    __tablename__ = "user_workspaces"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "workspace_id", "team_id",
            name="uq_user_workspaces"
        ),
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
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
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
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
    )
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="user_workspaces",
    )
    team: Mapped["Team"] = relationship("Team")
    granter: Mapped["User"] = relationship(
        "User",
        foreign_keys=[granted_by],
    )

    def __repr__(self) -> str:
        return f"<UserWorkspace user={self.user_id} workspace={self.workspace_id}>"
