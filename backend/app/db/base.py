"""
SQLAlchemy Base class for all models.
Import all models here to ensure they are registered with SQLAlchemy.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Import all models here to ensure they are registered
# This is important for Alembic migrations
from app.models.user import User  # noqa: F401, E402
from app.models.team import Team  # noqa: F401, E402
from app.models.role import Role  # noqa: F401, E402
from app.models.workspace import Workspace  # noqa: F401, E402
from app.models.permission import Permission  # noqa: F401, E402
from app.models.team_member import TeamMember  # noqa: F401, E402
from app.models.role_permission import RolePermission  # noqa: F401, E402
from app.models.team_workspace import TeamWorkspace  # noqa: F401, E402
from app.models.user_workspace import UserWorkspace  # noqa: F401, E402
from app.models.team_permission import TeamPermission  # noqa: F401, E402
from app.models.invitation import Invitation  # noqa: F401, E402
from app.models.oauth_client import OAuthClient  # noqa: F401, E402
from app.models.oauth_authorization_code import OAuthAuthorizationCode  # noqa: F401, E402
from app.models.refresh_token import RefreshToken  # noqa: F401, E402
from app.models.activity_log import ActivityLog  # noqa: F401, E402
