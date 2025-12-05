"""
OAuth2/OIDC schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema, TimestampMixin


class OAuthClientCreate(BaseSchema):
    """Schema for creating an OAuth client."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    client_type: str = Field(default="confidential")  # 'public' or 'confidential'
    redirect_uris: list[str] = Field(..., min_length=1)
    allowed_scopes: list[str] = Field(default=["openid", "profile", "email"])

    @field_validator("client_type")
    @classmethod
    def validate_client_type(cls, v: str) -> str:
        if v not in ("public", "confidential"):
            raise ValueError("client_type must be 'public' or 'confidential'")
        return v

    @field_validator("redirect_uris")
    @classmethod
    def validate_redirect_uris(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one redirect_uri is required")
        return v


class OAuthClientUpdate(BaseSchema):
    """Schema for updating an OAuth client."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    redirect_uris: Optional[list[str]] = None
    allowed_scopes: Optional[list[str]] = None
    is_active: Optional[bool] = None


class OAuthClientResponse(BaseSchema, TimestampMixin):
    """Schema for OAuth client response."""

    id: UUID
    client_id: str
    name: str
    description: Optional[str] = None
    client_type: str
    redirect_uris: list[str]
    allowed_scopes: list[str]
    is_active: bool


class OAuthClientWithSecret(OAuthClientResponse):
    """OAuth client response with secret (only on creation)."""

    client_secret: str


class AuthorizationRequest(BaseSchema):
    """Schema for OAuth authorization request."""

    response_type: str  # 'code'
    client_id: str
    redirect_uri: str
    scope: Optional[str] = None
    state: Optional[str] = None
    nonce: Optional[str] = None  # For OIDC
    code_challenge: Optional[str] = None  # For PKCE
    code_challenge_method: Optional[str] = None  # 'S256' or 'plain'

    @field_validator("response_type")
    @classmethod
    def validate_response_type(cls, v: str) -> str:
        if v != "code":
            raise ValueError("Only 'code' response_type is supported")
        return v

    @field_validator("code_challenge_method")
    @classmethod
    def validate_code_challenge_method(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("S256", "plain"):
            raise ValueError("code_challenge_method must be 'S256' or 'plain'")
        return v


class TokenRequest(BaseSchema):
    """Schema for OAuth token request."""

    grant_type: str  # 'authorization_code' or 'refresh_token'
    code: Optional[str] = None  # For authorization_code grant
    redirect_uri: Optional[str] = None
    client_id: str
    client_secret: Optional[str] = None  # For confidential clients
    code_verifier: Optional[str] = None  # For PKCE
    refresh_token: Optional[str] = None  # For refresh_token grant

    @field_validator("grant_type")
    @classmethod
    def validate_grant_type(cls, v: str) -> str:
        if v not in ("authorization_code", "refresh_token"):
            raise ValueError("grant_type must be 'authorization_code' or 'refresh_token'")
        return v


class OAuthTokenResponse(BaseSchema):
    """Schema for OAuth token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None  # For OIDC


class UserInfoResponse(BaseSchema):
    """Schema for OIDC UserInfo response."""

    sub: str  # user_id
    email: Optional[str] = None
    email_verified: bool = True
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    teams: Optional[list["TeamClaim"]] = None
    roles: Optional[list["RoleClaim"]] = None
    workspaces: Optional[list["WorkspaceClaim"]] = None
    permissions: Optional[list["PermissionClaim"]] = None


class TeamClaim(BaseSchema):
    """Team info for ID token claims."""

    name: str
    slug: str


class RoleClaim(BaseSchema):
    """Role info for ID token claims."""

    name: str
    slug: str


class WorkspaceClaim(BaseSchema):
    """Workspace info for ID token claims."""

    name: str
    slug: str


class PermissionClaim(BaseSchema):
    """Permission info for ID token claims."""

    name: str
    slug: str


class OIDCDiscovery(BaseSchema):
    """Schema for OIDC Discovery document."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str
    revocation_endpoint: str
    introspection_endpoint: str
    response_types_supported: list[str] = ["code"]
    grant_types_supported: list[str] = ["authorization_code", "refresh_token"]
    subject_types_supported: list[str] = ["public"]
    id_token_signing_alg_values_supported: list[str] = ["RS256"]
    scopes_supported: list[str] = [
        "openid", "profile", "email", "teams", "roles", "workspaces", "permissions"
    ]
    token_endpoint_auth_methods_supported: list[str] = [
        "client_secret_basic", "client_secret_post"
    ]
    claims_supported: list[str] = [
        "sub", "email", "given_name", "family_name", "name", "picture",
        "teams", "roles", "workspaces", "permissions"
    ]
    code_challenge_methods_supported: list[str] = ["S256", "plain"]


class JWK(BaseSchema):
    """Schema for JSON Web Key."""

    kty: str
    use: str
    kid: str
    alg: str
    n: str
    e: str


class JWKS(BaseSchema):
    """Schema for JSON Web Key Set."""

    keys: list[JWK]


# Update forward references
UserInfoResponse.model_rebuild()
