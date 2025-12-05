"""
User service for user management operations.
"""

import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.models.team_member import TeamMember
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_user_count(self) -> int:
        """Get total number of users."""
        result = await self.db.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def has_users(self) -> bool:
        """Check if any users exist in the system."""
        count = await self.get_user_count()
        return count > 0

    async def get_system_owner(self) -> Optional[User]:
        """Get the system owner user."""
        result = await self.db.execute(
            select(User).where(User.is_system_owner == True)
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        is_system_owner: bool = False,
        avatar_url: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        user = User(
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            password_hash=get_password_hash(password),
            is_system_owner=is_system_owner,
            avatar_url=avatar_url,
            is_active=True,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_user(
        self,
        user: User,
        update_data: UserUpdate,
    ) -> User:
        """Update user profile."""
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_avatar(
        self,
        user: User,
        avatar_url: Optional[str] = None,
        avatar_path: Optional[str] = None,
    ) -> User:
        """Update user avatar."""
        if avatar_url:
            user.avatar_url = avatar_url
            user.avatar_path = None
        elif avatar_path:
            user.avatar_path = avatar_path
            user.avatar_url = None

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def change_password(
        self,
        user: User,
        new_password: str,
    ) -> User:
        """Change user password."""
        user.password_hash = get_password_hash(new_password)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_by_email(email)
        if not user:
            return None
        if not user.password_hash:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user

    async def get_user_with_teams(
        self,
        user_id: uuid.UUID,
    ) -> Optional[User]:
        """Get user with team memberships loaded."""
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.team_memberships)
                .selectinload(TeamMember.team),
                selectinload(User.team_memberships)
                .selectinload(TeamMember.role),
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def deactivate_user(self, user: User) -> User:
        """Deactivate a user."""
        user.is_active = False
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def activate_user(self, user: User) -> User:
        """Activate a user."""
        user.is_active = True
        await self.db.commit()
        await self.db.refresh(user)
        return user
