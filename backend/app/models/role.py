"""
Role model for team-specific roles.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.team_member import TeamMember
    from app.models.role_permission import RolePermission
    from app.models.invitation import Invitation


class Role(Base):
    """
    Role model for team-specific roles.

    Each team can have its own roles with different permissions.
    Admin roles have special privileges within the team.
    Priority determines role hierarchy (higher = more important).
    """

    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint(
            r"slug ~ '^[a-zA-Z0-9_]+$'",
            name="roles_slug_format",
        ),
        CheckConstraint(
            "priority >= 0",
            name="roles_priority_non_negative",
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
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="roles",
    )
    team_members: Mapped[List["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="role",
    )
    role_permissions: Mapped[List["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[List["Invitation"]] = relationship(
        "Invitation",
        back_populates="role",
    )

    def __repr__(self) -> str:
        return f"<Role {self.slug}>"
