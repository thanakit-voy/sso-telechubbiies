"""
Invitation model for user invitations.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.team import Team
    from app.models.role import Role


class InvitationType(str, Enum):
    """Types of invitations."""
    SYSTEM_OWNER = "system_owner"
    TEAM_MEMBER = "team_member"


class InvitationStatus(str, Enum):
    """Status of invitations."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Invitation(Base):
    """
    Invitation model for user invitations.

    Used for both system owner bootstrap and team member invitations.
    Each invitation has a unique token and can only be used once.
    """

    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    invitation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
    )
    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
    )
    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,  # NULL for system owner bootstrap
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=InvitationStatus.PENDING.value,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    team: Mapped[Optional["Team"]] = relationship(
        "Team",
        back_populates="invitations",
    )
    role: Mapped[Optional["Role"]] = relationship(
        "Role",
        back_populates="invitations",
    )
    invited_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="sent_invitations",
        foreign_keys=[invited_by],
    )

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_pending(self) -> bool:
        """Check if invitation is still pending."""
        return self.status == InvitationStatus.PENDING.value

    @property
    def is_valid(self) -> bool:
        """Check if invitation can be accepted."""
        return self.is_pending and not self.is_expired

    def __repr__(self) -> str:
        return f"<Invitation {self.email} ({self.status})>"
