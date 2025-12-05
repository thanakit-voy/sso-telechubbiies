"""
API v1 router - combines all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    system,
    auth,
    invitations,
    teams,
    roles,
    workspaces,
    permissions,
    activity_logs,
    oauth,
)

api_router = APIRouter()

# System endpoints
api_router.include_router(
    system.router,
    prefix="/system",
    tags=["system"],
)

# Auth endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"],
)

# Invitation endpoints
api_router.include_router(
    invitations.router,
    prefix="/invitations",
    tags=["invitations"],
)

# Team endpoints
api_router.include_router(
    teams.router,
    prefix="/teams",
    tags=["teams"],
)

# Role endpoints
api_router.include_router(
    roles.router,
    prefix="/roles",
    tags=["roles"],
)

# Workspace endpoints
api_router.include_router(
    workspaces.router,
    prefix="/workspaces",
    tags=["workspaces"],
)

# Permission endpoints
api_router.include_router(
    permissions.router,
    prefix="/permissions",
    tags=["permissions"],
)

# Activity log endpoints
api_router.include_router(
    activity_logs.router,
    prefix="/activity",
    tags=["activity"],
)

# OAuth/OIDC endpoints
api_router.include_router(
    oauth.router,
    prefix="/oauth",
    tags=["oauth"],
)
