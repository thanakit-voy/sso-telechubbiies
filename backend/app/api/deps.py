"""
API dependencies for dependency injection.
"""

from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.services.user_service import UserService
from app.services.team_service import TeamService
from app.services.invitation_service import InvitationService
from app.services.permission_service import PermissionService
from app.services.activity_service import ActivityService

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    """Get UserService instance."""
    return UserService(db)


async def get_team_service(
    db: AsyncSession = Depends(get_db),
) -> TeamService:
    """Get TeamService instance."""
    return TeamService(db)


async def get_invitation_service(
    db: AsyncSession = Depends(get_db),
) -> InvitationService:
    """Get InvitationService instance."""
    return InvitationService(db)


async def get_permission_service(
    db: AsyncSession = Depends(get_db),
) -> PermissionService:
    """Get PermissionService instance."""
    return PermissionService(db)


async def get_activity_service(
    db: AsyncSession = Depends(get_db),
) -> ActivityService:
    """Get ActivityService instance."""
    return ActivityService(db)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    user_service: UserService = Depends(get_user_service),
) -> Optional[User]:
    """
    Get current user from token if provided.
    Returns None if no valid token.
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        return None

    if payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        user = await user_service.get_by_id(UUID(user_id))
        if user and user.is_active:
            return user
    except (ValueError, TypeError):
        pass

    return None


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """
    Get current user from token.
    Raises 401 if not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user.
    Raises 403 if user is inactive.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    return user


async def get_current_system_owner(
    user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current user if they are system owner.
    Raises 403 if not system owner.
    """
    if not user.is_system_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System owner access required",
        )
    return user


def get_client_ip(request: Request) -> Optional[str]:
    """Get client IP address from request."""
    # Try X-Forwarded-For header first (for proxied requests)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Fall back to client host
    if request.client:
        return request.client.host

    return None


def get_user_agent(request: Request) -> Optional[str]:
    """Get user agent from request."""
    return request.headers.get("User-Agent")


class TeamAdminChecker:
    """
    Dependency class to check if user is admin of a specific team.
    """

    async def __call__(
        self,
        team_slug: str,
        current_user: User = Depends(get_current_active_user),
        team_service: TeamService = Depends(get_team_service),
    ) -> User:
        """Check if current user is admin of the team."""
        team = await team_service.get_team_by_slug(team_slug)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found",
            )

        # System owner has admin access to all teams
        if current_user.is_system_owner:
            return current_user

        # Check if user is team owner
        if team.owner_id == current_user.id:
            return current_user

        # Check if user has admin role in team
        is_admin = await team_service.is_team_admin(team.id, current_user.id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required for this team",
            )

        return current_user


# Instance for dependency injection
require_team_admin = TeamAdminChecker()
