"""
Permission model for access control.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.role_permission import RolePermission
    from app.models.team_permission import TeamPermission


class Permission(Base):
    """
    Permission model for access control.

    Permissions can be global (created by owner, team_id=NULL)
    or team-specific (created by team admin).
    """

    __tablename__ = "permissions"
    __table_args__ = (
        CheckConstraint(
            r"slug ~ '^[a-zA-Z0-9_]+$'",
            name="permissions_slug_format",
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
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,  # NULL = global permission created by owner
        index=True,
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
    team: Mapped[Optional["Team"]] = relationship("Team")
    role_permissions: Mapped[List["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )
    team_permissions: Mapped[List["TeamPermission"]] = relationship(
        "TeamPermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )

    @property
    def is_global(self) -> bool:
        """Check if this is a global permission."""
        return self.team_id is None

    def __repr__(self) -> str:
        return f"<Permission {self.slug}>"
