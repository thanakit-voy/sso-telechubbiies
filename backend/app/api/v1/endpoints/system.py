"""
System endpoints for bootstrap and status.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_user_service,
    get_invitation_service,
    get_activity_service,
    get_client_ip,
)
from app.core.config import settings
from app.services.user_service import UserService
from app.services.invitation_service import InvitationService
from app.services.activity_service import ActivityService
from app.services.email_service import email_service
from app.schemas.auth import SystemStatus
from app.schemas.invitation import BootstrapRequest, BootstrapResponse

router = APIRouter()


@router.get("/status", response_model=SystemStatus)
async def get_system_status(
    user_service: UserService = Depends(get_user_service),
):
    """
    Get system initialization status.

    Returns whether the system has been initialized (has users).
    """
    user_count = await user_service.get_user_count()
    initialized = user_count > 0

    if initialized:
        message = "System is initialized"
    else:
        message = "System requires initialization. Create the first user to get started."

    return SystemStatus(
        initialized=initialized,
        user_count=user_count,
        message=message,
    )


@router.post("/bootstrap", response_model=BootstrapResponse)
async def bootstrap_system(
    request: Request,
    data: BootstrapRequest,
    user_service: UserService = Depends(get_user_service),
    invitation_service: InvitationService = Depends(get_invitation_service),
):
    """
    Bootstrap the system by creating the first user invitation.

    This endpoint can only be called when there are no users in the system.
    It creates an invitation for the system owner.
    """
    # Check if system already has users
    has_users = await user_service.has_users()
    if has_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System already initialized. Cannot bootstrap again.",
        )

    # Check for existing pending invitations
    pending = await invitation_service.get_pending_for_email(data.email)
    if pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invitation already exists for this email",
        )

    # Create system owner invitation
    invitation = await invitation_service.create_system_owner_invitation(data.email)
    invitation_link = invitation_service.get_invitation_link(invitation.token)

    # Send invitation email
    email_sent = await email_service.send_invitation_email(
        to_email=data.email,
        invitation_link=invitation_link,
    )

    if email_sent:
        message = f"Invitation sent to {data.email}. Check your email to complete registration."
    else:
        message = "Invitation created but email could not be sent."

    response = BootstrapResponse(
        message=message,
    )

    # In development, include the token for easier testing
    if settings.is_development:
        response.invitation_token = invitation.token

    return response
