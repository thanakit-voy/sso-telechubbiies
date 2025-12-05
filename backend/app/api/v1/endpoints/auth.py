"""
Authentication endpoints.
"""

from datetime import timedelta, timezone, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_user_service,
    get_activity_service,
    get_current_user,
    get_current_active_user,
    get_client_ip,
    get_user_agent,
)
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_token,
)
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.services.user_service import UserService
from app.services.activity_service import ActivityService
from app.schemas.auth import (
    LoginRequest,
    AuthResponse,
    TokenResponse,
    RefreshRequest,
    SessionInfo,
    TeamMembershipInfo,
)
from app.schemas.user import UserResponse, UserUpdate, PasswordChange
from app.core.security import verify_password

router = APIRouter()


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """
    Authenticate user with email and password.

    Returns access token and user info. Also sets httpOnly cookie for refresh token.
    """
    # Authenticate user
    user = await user_service.authenticate(data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
    )

    # Create refresh token
    raw_refresh, hashed_refresh = create_refresh_token(data={"sub": str(user.id)})

    # Store refresh token in database
    refresh_token = RefreshToken(
        token_hash=hashed_refresh,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_token)
    await db.commit()

    # Set refresh token in httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

    # Log activity
    await activity_service.log_login(
        user_id=user.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """
    Logout user by revoking refresh token.
    """
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")

    if refresh_token:
        # Revoke refresh token
        from sqlalchemy import select, update

        token_hash = hash_token(refresh_token)
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(revoked=True)
        )
        await db.commit()

    # Clear cookie
    response.delete_cookie(
        key="refresh_token",
        path="/",
    )

    # Log activity
    await activity_service.log_logout(
        user_id=current_user.id,
        ip_address=get_client_ip(request),
    )

    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    """
    Refresh access token using refresh token from cookie.
    """
    from sqlalchemy import select

    # Get refresh token from cookie
    raw_refresh = request.cookies.get("refresh_token")
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    # Find refresh token in database
    token_hash = hash_token(raw_refresh)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if not token_record.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or revoked",
        )

    # Get user
    user = await user_service.get_by_id(token_record.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Revoke old refresh token (rotation)
    token_record.revoked = True

    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    raw_new_refresh, hashed_new_refresh = create_refresh_token(data={"sub": str(user.id)})

    # Store new refresh token
    new_refresh_token = RefreshToken(
        token_hash=hashed_new_refresh,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_refresh_token)
    await db.commit()

    # Set new refresh token in cookie
    response.set_cookie(
        key="refresh_token",
        value=raw_new_refresh,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=SessionInfo)
async def get_current_session(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    """
    Get current user session info including teams and permissions.
    """
    # Get user with team memberships
    user_with_teams = await user_service.get_user_with_teams(current_user.id)

    teams = []
    permissions = set()

    if user_with_teams:
        for membership in user_with_teams.team_memberships:
            team_info = TeamMembershipInfo(
                id=membership.team.id,
                name=membership.team.name,
                slug=membership.team.slug,
                role_name=membership.role.name if membership.role else None,
                role_slug=membership.role.slug if membership.role else None,
                is_admin=membership.role.is_admin if membership.role else False,
            )
            teams.append(team_info)

            # Collect permissions from roles
            if membership.role:
                for rp in membership.role.role_permissions:
                    permissions.add(rp.permission.slug)

    return SessionInfo(
        user=UserResponse.model_validate(current_user),
        is_system_owner=current_user.is_system_owner,
        teams=teams,
        permissions=list(permissions),
    )


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    """
    Update current user's profile.

    Allowed fields: first_name, last_name, avatar_url
    """
    updated_user = await user_service.update_user(current_user, data)
    return UserResponse.model_validate(updated_user)


@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    """
    Change current user's password.

    Requires current password for verification.
    """
    # Verify current password
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no password set",
        )

    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Change password
    await user_service.change_password(current_user, data.new_password)

    return {"message": "Password changed successfully"}
