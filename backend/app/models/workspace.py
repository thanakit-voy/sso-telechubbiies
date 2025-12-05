"""
Workspace model for work areas/projects.
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
    from app.models.team_workspace import TeamWorkspace
    from app.models.user_workspace import UserWorkspace


class Workspace(Base):
    """
    Workspace model for work areas/projects.

    Only system owner can create workspaces.
    Workspaces are granted to teams by owner, then to users by team admins.
    """

    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint(
            r"slug ~ '^[a-zA-Z0-9_]+$'",
            name="workspaces_slug_format",
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
    created_by: Mapped[uuid.UUID] = mapped_column(
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
    creator: Mapped["User"] = relationship("User")
    team_workspaces: Mapped[List["TeamWorkspace"]] = relationship(
        "TeamWorkspace",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    user_workspaces: Mapped[List["UserWorkspace"]] = relationship(
        "UserWorkspace",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Workspace {self.slug}>"
