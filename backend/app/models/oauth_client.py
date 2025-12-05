"""
OAuthClient model for OAuth2/OIDC client applications.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.oauth_authorization_code import OAuthAuthorizationCode
    from app.models.refresh_token import RefreshToken


class ClientType(str, Enum):
    """OAuth client types."""
    PUBLIC = "public"
    CONFIDENTIAL = "confidential"


class OAuthClient(Base):
    """
    OAuth2/OIDC client application model.

    Represents external applications that can use Telechubbiies SSO.
    """

    __tablename__ = "oauth_clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    client_secret_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,  # NULL for public clients
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ClientType.CONFIDENTIAL.value,
    )
    redirect_uris: Mapped[List[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
    )
    allowed_scopes: Mapped[List[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
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
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="oauth_clients",
    )
    authorization_codes: Mapped[List["OAuthAuthorizationCode"]] = relationship(
        "OAuthAuthorizationCode",
        back_populates="client",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="client",
        cascade="all, delete-orphan",
    )

    @property
    def is_public(self) -> bool:
        """Check if this is a public client."""
        return self.client_type == ClientType.PUBLIC.value

    @property
    def is_confidential(self) -> bool:
        """Check if this is a confidential client."""
        return self.client_type == ClientType.CONFIDENTIAL.value

    def validate_redirect_uri(self, redirect_uri: str) -> bool:
        """Validate that redirect_uri is allowed."""
        return redirect_uri in self.redirect_uris

    def validate_scopes(self, scopes: List[str]) -> bool:
        """Validate that all requested scopes are allowed."""
        return all(scope in self.allowed_scopes for scope in scopes)

    def __repr__(self) -> str:
        return f"<OAuthClient {self.client_id}>"
