"""
User model for storing user account information.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.team_member import TeamMember
    from app.models.invitation import Invitation
    from app.models.oauth_client import OAuthClient
    from app.models.refresh_token import RefreshToken
    from app.models.activity_log import ActivityLog


class User(Base):
    """
    User account model.

    Stores basic user information and authentication credentials.
    Users can only be created through invitations (no public signup).
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    avatar_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_system_owner: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
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
    owned_teams: Mapped[List["Team"]] = relationship(
        "Team",
        back_populates="owner",
        foreign_keys="Team.owner_id",
    )
    team_memberships: Mapped[List["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sent_invitations: Mapped[List["Invitation"]] = relationship(
        "Invitation",
        back_populates="invited_by_user",
        foreign_keys="Invitation.invited_by",
    )
    oauth_clients: Mapped[List["OAuthClient"]] = relationship(
        "OAuthClient",
        back_populates="owner",
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    activity_logs: Mapped[List["ActivityLog"]] = relationship(
        "ActivityLog",
        back_populates="actor",
    )

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def avatar(self) -> Optional[str]:
        """Get user's avatar URL (external URL or local path)."""
        return self.avatar_url or self.avatar_path

    def __repr__(self) -> str:
        return f"<User {self.email}>"
