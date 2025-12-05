"""
OAuthAuthorizationCode model for OAuth2 authorization codes.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.oauth_client import OAuthClient


class OAuthAuthorizationCode(Base):
    """
    OAuth2 authorization code model.

    Stores authorization codes during the authorization code flow.
    Supports PKCE for public clients.
    """

    __tablename__ = "oauth_authorization_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("oauth_clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    redirect_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nonce: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    code_challenge: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,  # For PKCE
    )
    code_challenge_method: Mapped[Optional[str]] = mapped_column(
        String(10),  # 'S256' or 'plain'
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    client: Mapped["OAuthClient"] = relationship(
        "OAuthClient",
        back_populates="authorization_codes",
    )
    user: Mapped["User"] = relationship("User")

    @property
    def is_expired(self) -> bool:
        """Check if code has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if code can be used."""
        return not self.used and not self.is_expired

    @property
    def requires_pkce(self) -> bool:
        """Check if PKCE verification is required."""
        return self.code_challenge is not None

    def __repr__(self) -> str:
        return f"<OAuthAuthorizationCode {self.code[:8]}...>"
