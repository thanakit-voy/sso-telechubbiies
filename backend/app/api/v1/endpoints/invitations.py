"""
Invitation endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_user_service,
    get_team_service,
    get_invitation_service,
    get_activity_service,
    get_current_active_user,
    get_client_ip,
    require_team_admin,
)
from app.core.config import settings
from app.models.user import User
from app.models.invitation import InvitationType
from app.services.user_service import UserService
from app.services.team_service import TeamService
from app.services.invitation_service import InvitationService
from app.services.activity_service import ActivityService
from app.services.email_service import email_service
from app.schemas.invitation import (
    InvitationCreate,
    InvitationResponse,
    InvitationAccept,
    InvitationValidation,
    InvitationLink,
    InvitationWithTeam,
)
from app.schemas.user import UserResponse, UserBrief

router = APIRouter()


@router.get("/{token}", response_model=InvitationValidation)
async def validate_invitation(
    token: str,
    invitation_service: InvitationService = Depends(get_invitation_service),
):
    """
    Validate an invitation token.

    Returns information about the invitation if valid.
    """
    is_valid, invitation, message = await invitation_service.validate_invitation(token)

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    response = InvitationValidation(
        valid=is_valid,
        email=invitation.email,
        invitation_type=invitation.invitation_type,
        team_name=invitation.team.name if invitation.team else None,
        role_name=invitation.role.name if invitation.role else None,
        expires_at=invitation.expires_at,
        message=message if not is_valid else None,
    )

    return response


@router.post("/{token}/accept", response_model=UserResponse)
async def accept_invitation(
    request: Request,
    token: str,
    data: InvitationAccept,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
    team_service: TeamService = Depends(get_team_service),
    invitation_service: InvitationService = Depends(get_invitation_service),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """
    Accept an invitation and create user account.

    For system owner invitations, creates the first user.
    For team invitations, creates user and adds to team.
    """
    # Validate invitation
    is_valid, invitation, message = await invitation_service.validate_invitation(token)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    # Check if user already exists
    existing_user = await user_service.get_by_email(invitation.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    # Determine if this is system owner
    is_system_owner = invitation.invitation_type == InvitationType.SYSTEM_OWNER.value

    # Create user
    user = await user_service.create_user(
        email=invitation.email,
        first_name=data.first_name,
        last_name=data.last_name,
        password=data.password,
        is_system_owner=is_system_owner,
        avatar_url=data.avatar_url,
    )

    # Mark invitation as accepted
    await invitation_service.accept_invitation(invitation)

    # For team invitations, add user to team
    if invitation.team_id and invitation.invitation_type == InvitationType.TEAM_MEMBER.value:
        await team_service.add_team_member(
            team_id=invitation.team_id,
            user_id=user.id,
            role_id=invitation.role_id,
        )

        # Log activity
        await activity_service.log_member_added(
            actor_id=invitation.invited_by or user.id,
            team_id=invitation.team_id,
            user_id=user.id,
            user_email=user.email,
            role_name=invitation.role.name if invitation.role else None,
            ip_address=get_client_ip(request),
        )

    # Send welcome email
    await email_service.send_welcome_email(
        to_email=user.email,
        first_name=user.first_name,
    )

    return UserResponse.model_validate(user)


@router.post("/team/{team_slug}", response_model=InvitationLink)
async def create_team_invitation(
    request: Request,
    team_slug: str,
    data: InvitationCreate,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
    invitation_service: InvitationService = Depends(get_invitation_service),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """
    Create an invitation to join a team.

    Only team admins can create invitations.
    """
    # Get team
    team = await team_service.get_team_by_slug(team_slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check for existing pending invitations
    pending = await invitation_service.get_pending_for_email(data.email)
    for inv in pending:
        if inv.team_id == team.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An invitation already exists for this email",
            )

    # If role specified, validate it belongs to the team
    if data.role_id:
        role = await team_service.get_role_by_id(data.role_id)
        if not role or role.team_id != team.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role for this team",
            )

    # Create invitation
    invitation = await invitation_service.create_team_invitation(
        email=data.email,
        team_id=team.id,
        invited_by=current_user.id,
        role_id=data.role_id,
    )

    invitation_link = invitation_service.get_invitation_link(invitation.token)

    # Send email if requested
    if data.send_email:
        await email_service.send_invitation_email(
            to_email=data.email,
            invitation_link=invitation_link,
            team_name=team.name,
            inviter_name=current_user.full_name,
        )

    # Log activity
    await activity_service.log_invitation_created(
        actor_id=current_user.id,
        invitation_id=invitation.id,
        email=data.email,
        team_id=team.id,
        ip_address=get_client_ip(request),
    )

    return InvitationLink(
        invitation_id=invitation.id,
        link=invitation_link,
        expires_at=invitation.expires_at,
    )


@router.get("/team/{team_slug}/pending", response_model=list[InvitationWithTeam])
async def get_team_pending_invitations(
    team_slug: str,
    current_user: User = Depends(require_team_admin),
    team_service: TeamService = Depends(get_team_service),
    invitation_service: InvitationService = Depends(get_invitation_service),
):
    """
    Get pending invitations for a team.

    Only team admins can view invitations.
    """
    team = await team_service.get_team_by_slug(team_slug)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    invitations = await invitation_service.get_team_pending_invitations(team.id)

    return [
        InvitationWithTeam(
            id=inv.id,
            email=inv.email,
            invitation_type=inv.invitation_type,
            team_id=inv.team_id,
            role_id=inv.role_id,
            status=inv.status,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
            team_name=team.name,
            team_slug=team.slug,
            role_name=inv.role.name if inv.role else None,
            invited_by=UserBrief(
                id=inv.invited_by_user.id,
                email=inv.invited_by_user.email,
                first_name=inv.invited_by_user.first_name,
                last_name=inv.invited_by_user.last_name,
            ) if inv.invited_by_user else None,
        )
        for inv in invitations
    ]


@router.delete("/{invitation_id}")
async def cancel_invitation(
    request: Request,
    invitation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
    invitation_service: InvitationService = Depends(get_invitation_service),
):
    """
    Cancel a pending invitation.

    Only the inviter or team admin can cancel.
    """
    invitation = await invitation_service.get_by_id(invitation_id)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if not invitation.is_pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel pending invitations",
        )

    # Check permissions
    can_cancel = False

    if invitation.invited_by == current_user.id:
        can_cancel = True
    elif current_user.is_system_owner:
        can_cancel = True
    elif invitation.team_id:
        is_admin = await team_service.is_team_admin(invitation.team_id, current_user.id)
        if is_admin:
            can_cancel = True

    if not can_cancel:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this invitation",
        )

    await invitation_service.cancel_invitation(invitation)

    return {"message": "Invitation cancelled"}
