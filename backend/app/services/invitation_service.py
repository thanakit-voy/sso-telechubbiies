"""
Invitation service for managing user invitations.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import generate_secure_token
from app.models.invitation import Invitation, InvitationType, InvitationStatus
from app.models.team import Team
from app.models.role import Role


class InvitationService:
    """Service for invitation management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, invitation_id: uuid.UUID) -> Optional[Invitation]:
        """Get invitation by ID."""
        result = await self.db.execute(
            select(Invitation).where(Invitation.id == invitation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> Optional[Invitation]:
        """Get invitation by token."""
        result = await self.db.execute(
            select(Invitation)
            .options(
                selectinload(Invitation.team),
                selectinload(Invitation.role),
                selectinload(Invitation.invited_by_user),
            )
            .where(Invitation.token == token)
        )
        return result.scalar_one_or_none()

    async def get_pending_for_email(self, email: str) -> list[Invitation]:
        """Get pending invitations for an email."""
        result = await self.db.execute(
            select(Invitation)
            .where(
                and_(
                    Invitation.email == email.lower(),
                    Invitation.status == InvitationStatus.PENDING.value,
                )
            )
        )
        return list(result.scalars().all())

    async def create_system_owner_invitation(self, email: str) -> Invitation:
        """Create an invitation for the system owner."""
        token = generate_secure_token(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.INVITATION_EXPIRE_HOURS
        )

        invitation = Invitation(
            email=email.lower(),
            token=token,
            invitation_type=InvitationType.SYSTEM_OWNER.value,
            expires_at=expires_at,
            status=InvitationStatus.PENDING.value,
        )

        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def create_team_invitation(
        self,
        email: str,
        team_id: uuid.UUID,
        invited_by: uuid.UUID,
        role_id: Optional[uuid.UUID] = None,
    ) -> Invitation:
        """Create an invitation to join a team."""
        token = generate_secure_token(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.INVITATION_EXPIRE_HOURS
        )

        invitation = Invitation(
            email=email.lower(),
            token=token,
            invitation_type=InvitationType.TEAM_MEMBER.value,
            team_id=team_id,
            role_id=role_id,
            invited_by=invited_by,
            expires_at=expires_at,
            status=InvitationStatus.PENDING.value,
        )

        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def validate_invitation(self, token: str) -> tuple[bool, Optional[Invitation], str]:
        """
        Validate an invitation token.

        Returns:
            Tuple of (is_valid, invitation, message)
        """
        invitation = await self.get_by_token(token)

        if not invitation:
            return False, None, "Invitation not found"

        if invitation.status == InvitationStatus.ACCEPTED.value:
            return False, invitation, "Invitation has already been used"

        if invitation.status == InvitationStatus.CANCELLED.value:
            return False, invitation, "Invitation has been cancelled"

        if invitation.status == InvitationStatus.EXPIRED.value:
            return False, invitation, "Invitation has expired"

        if invitation.is_expired:
            # Update status to expired
            invitation.status = InvitationStatus.EXPIRED.value
            await self.db.commit()
            return False, invitation, "Invitation has expired"

        return True, invitation, "Invitation is valid"

    async def accept_invitation(self, invitation: Invitation) -> Invitation:
        """Mark invitation as accepted."""
        invitation.status = InvitationStatus.ACCEPTED.value
        invitation.accepted_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def cancel_invitation(self, invitation: Invitation) -> Invitation:
        """Cancel an invitation."""
        invitation.status = InvitationStatus.CANCELLED.value
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def get_team_pending_invitations(self, team_id: uuid.UUID) -> list[Invitation]:
        """Get pending invitations for a team."""
        result = await self.db.execute(
            select(Invitation)
            .options(selectinload(Invitation.role))
            .where(
                and_(
                    Invitation.team_id == team_id,
                    Invitation.status == InvitationStatus.PENDING.value,
                )
            )
        )
        return list(result.scalars().all())

    async def expire_old_invitations(self) -> int:
        """Expire all overdue pending invitations. Returns count of expired."""
        now = datetime.now(timezone.utc)

        result = await self.db.execute(
            select(Invitation).where(
                and_(
                    Invitation.status == InvitationStatus.PENDING.value,
                    Invitation.expires_at < now,
                )
            )
        )
        invitations = result.scalars().all()

        count = 0
        for invitation in invitations:
            invitation.status = InvitationStatus.EXPIRED.value
            count += 1

        if count > 0:
            await self.db.commit()

        return count

    def get_invitation_link(self, token: str) -> str:
        """Generate the full invitation link."""
        return f"{settings.FRONTEND_URL}/invite/accept?token={token}"
