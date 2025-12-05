"""
OAuth2/OIDC endpoints.
"""

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from cryptography.hazmat.primitives import serialization
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_user_service,
    get_team_service,
    get_permission_service,
    get_activity_service,
    get_current_active_user,
    get_current_system_owner,
    get_client_ip,
    get_user_agent,
)
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_id_token,
    create_refresh_token,
    hash_token,
    verify_code_challenge,
    generate_client_credentials,
    get_password_hash,
    verify_password,
    get_public_key,
    generate_secure_token,
)
from app.models.user import User
from app.models.oauth_client import OAuthClient
from app.models.oauth_authorization_code import OAuthAuthorizationCode
from app.models.refresh_token import RefreshToken
from app.services.user_service import UserService
from app.services.team_service import TeamService
from app.services.permission_service import PermissionService
from app.services.activity_service import ActivityService
from app.schemas.oauth import (
    OAuthClientCreate,
    OAuthClientUpdate,
    OAuthClientResponse,
    OAuthClientWithSecret,
    OAuthTokenResponse,
    UserInfoResponse,
    OIDCDiscovery,
    JWKS,
    JWK,
    TeamClaim,
    RoleClaim,
    WorkspaceClaim,
    PermissionClaim,
)

router = APIRouter()


# ==================== OIDC Discovery ====================

@router.get("/.well-known/openid-configuration", response_model=OIDCDiscovery)
async def openid_configuration():
    """OIDC Discovery endpoint."""
    base_url = settings.BACKEND_URL

    return OIDCDiscovery(
        issuer=base_url,
        authorization_endpoint=f"{base_url}/oauth/authorize",
        token_endpoint=f"{base_url}/oauth/token",
        userinfo_endpoint=f"{base_url}/oauth/userinfo",
        jwks_uri=f"{base_url}/oauth/.well-known/jwks.json",
        revocation_endpoint=f"{base_url}/oauth/revoke",
        introspection_endpoint=f"{base_url}/oauth/introspect",
    )


@router.get("/.well-known/jwks.json", response_model=JWKS)
async def jwks():
    """JSON Web Key Set endpoint."""
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    public_key_pem = get_public_key()
    public_key = load_pem_public_key(public_key_pem.encode())

    # Get public key numbers
    numbers = public_key.public_numbers()

    # Convert to base64url encoding
    def int_to_base64url(n: int) -> str:
        byte_length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(
            n.to_bytes(byte_length, byteorder='big')
        ).rstrip(b'=').decode('ascii')

    jwk = JWK(
        kty="RSA",
        use="sig",
        kid="telechubbiies-key-1",
        alg="RS256",
        n=int_to_base64url(numbers.n),
        e=int_to_base64url(numbers.e),
    )

    return JWKS(keys=[jwk])


# ==================== OAuth Client Management ====================

@router.get("/clients", response_model=List[OAuthClientResponse])
async def list_oauth_clients(
    current_user: User = Depends(get_current_system_owner),
    db: AsyncSession = Depends(get_db),
):
    """List OAuth clients. Only system owner."""
    from sqlalchemy import select

    result = await db.execute(
        select(OAuthClient).where(OAuthClient.owner_id == current_user.id)
    )
    clients = result.scalars().all()

    return [OAuthClientResponse.model_validate(c) for c in clients]


@router.post("/clients", response_model=OAuthClientWithSecret)
async def create_oauth_client(
    data: OAuthClientCreate,
    current_user: User = Depends(get_current_system_owner),
    db: AsyncSession = Depends(get_db),
):
    """Create a new OAuth client. Only system owner."""
    client_id, client_secret = generate_client_credentials()

    client = OAuthClient(
        client_id=client_id,
        client_secret_hash=get_password_hash(client_secret) if data.client_type == "confidential" else None,
        name=data.name,
        description=data.description,
        client_type=data.client_type,
        redirect_uris=data.redirect_uris,
        allowed_scopes=data.allowed_scopes,
        owner_id=current_user.id,
    )

    db.add(client)
    await db.commit()
    await db.refresh(client)

    return OAuthClientWithSecret(
        id=client.id,
        client_id=client.client_id,
        client_secret=client_secret if data.client_type == "confidential" else "",
        name=client.name,
        description=client.description,
        client_type=client.client_type,
        redirect_uris=client.redirect_uris,
        allowed_scopes=client.allowed_scopes,
        is_active=client.is_active,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


@router.get("/clients/{client_id}", response_model=OAuthClientResponse)
async def get_oauth_client(
    client_id: UUID,
    current_user: User = Depends(get_current_system_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get OAuth client details."""
    from sqlalchemy import select

    result = await db.execute(
        select(OAuthClient).where(OAuthClient.id == client_id)
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    if client.owner_id != current_user.id and not current_user.is_system_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    return OAuthClientResponse.model_validate(client)


@router.delete("/clients/{client_id}")
async def delete_oauth_client(
    client_id: UUID,
    current_user: User = Depends(get_current_system_owner),
    db: AsyncSession = Depends(get_db),
):
    """Delete an OAuth client."""
    from sqlalchemy import select

    result = await db.execute(
        select(OAuthClient).where(OAuthClient.id == client_id)
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    await db.delete(client)
    await db.commit()

    return {"message": "Client deleted"}


@router.post("/clients/{client_id}/rotate-secret", response_model=OAuthClientWithSecret)
async def rotate_client_secret(
    client_id: UUID,
    current_user: User = Depends(get_current_system_owner),
    db: AsyncSession = Depends(get_db),
):
    """Rotate client secret for confidential clients."""
    from sqlalchemy import select

    result = await db.execute(
        select(OAuthClient).where(OAuthClient.id == client_id)
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    if client.client_type != "confidential":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Public clients don't have secrets",
        )

    # Generate new secret
    _, new_secret = generate_client_credentials()
    client.client_secret_hash = get_password_hash(new_secret)
    await db.commit()
    await db.refresh(client)

    return OAuthClientWithSecret(
        id=client.id,
        client_id=client.client_id,
        client_secret=new_secret,
        name=client.name,
        description=client.description,
        client_type=client.client_type,
        redirect_uris=client.redirect_uris,
        allowed_scopes=client.allowed_scopes,
        is_active=client.is_active,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


# ==================== OAuth2 Authorization Flow ====================

@router.get("/authorize")
async def authorize(
    request: Request,
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    nonce: Optional[str] = Query(None),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth2 Authorization endpoint.

    If user is authenticated, generates authorization code.
    If not, redirects to login.
    """
    from sqlalchemy import select

    # Validate response_type
    if response_type != "code":
        return RedirectResponse(
            url=f"{redirect_uri}?error=unsupported_response_type&state={state or ''}"
        )

    # Find client
    result = await db.execute(
        select(OAuthClient).where(OAuthClient.client_id == client_id)
    )
    client = result.scalar_one_or_none()

    if not client or not client.is_active:
        return RedirectResponse(
            url=f"{redirect_uri}?error=invalid_client&state={state or ''}"
        )

    # Validate redirect_uri
    if not client.validate_redirect_uri(redirect_uri):
        return RedirectResponse(
            url=f"{redirect_uri}?error=invalid_redirect_uri&state={state or ''}"
        )

    # Validate scopes
    requested_scopes = scope.split() if scope else ["openid"]
    if not client.validate_scopes(requested_scopes):
        return RedirectResponse(
            url=f"{redirect_uri}?error=invalid_scope&state={state or ''}"
        )

    # Check PKCE for public clients
    if client.is_public and not code_challenge:
        return RedirectResponse(
            url=f"{redirect_uri}?error=invalid_request&error_description=PKCE+required&state={state or ''}"
        )

    if not current_user:
        # Redirect to login with return URL
        login_url = f"{settings.FRONTEND_URL}/login?return_to={request.url}"
        return RedirectResponse(url=login_url)

    # Generate authorization code
    code = generate_secure_token(32)

    auth_code = OAuthAuthorizationCode(
        code=code,
        client_id=client.id,
        user_id=current_user.id,
        redirect_uri=redirect_uri,
        scope=scope,
        nonce=nonce,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method or "S256",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )

    db.add(auth_code)
    await db.commit()

    # Redirect with code
    redirect_url = f"{redirect_uri}?code={code}"
    if state:
        redirect_url += f"&state={state}"

    return RedirectResponse(url=redirect_url)


@router.post("/token", response_model=OAuthTokenResponse)
async def token(
    request: Request,
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
    activity_service: ActivityService = Depends(get_activity_service),
):
    """OAuth2 Token endpoint."""
    from sqlalchemy import select

    # Find client
    result = await db.execute(
        select(OAuthClient).where(OAuthClient.client_id == client_id)
    )
    client = result.scalar_one_or_none()

    if not client or not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client",
        )

    # Verify client secret for confidential clients
    if client.is_confidential:
        if not client_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Client secret required",
            )
        if not verify_password(client_secret, client.client_secret_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client secret",
            )

    if grant_type == "authorization_code":
        return await _handle_authorization_code_grant(
            db, client, code, redirect_uri, code_verifier,
            user_service, team_service, permission_service,
            activity_service, request,
        )
    elif grant_type == "refresh_token":
        return await _handle_refresh_token_grant(
            db, client, refresh_token, user_service
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported grant type",
        )


async def _handle_authorization_code_grant(
    db: AsyncSession,
    client: OAuthClient,
    code: Optional[str],
    redirect_uri: Optional[str],
    code_verifier: Optional[str],
    user_service: UserService,
    team_service: TeamService,
    permission_service: PermissionService,
    activity_service: ActivityService,
    request: Request,
) -> OAuthTokenResponse:
    """Handle authorization_code grant."""
    from sqlalchemy import select

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code required",
        )

    # Find authorization code
    result = await db.execute(
        select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code == code)
    )
    auth_code = result.scalar_one_or_none()

    if not auth_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authorization code",
        )

    if not auth_code.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code expired or already used",
        )

    if auth_code.client_id != client.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client mismatch",
        )

    if auth_code.redirect_uri != redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect URI mismatch",
        )

    # Verify PKCE
    if auth_code.requires_pkce:
        if not code_verifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code verifier required",
            )
        if not verify_code_challenge(
            code_verifier,
            auth_code.code_challenge,
            auth_code.code_challenge_method,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid code verifier",
            )

    # Mark code as used
    auth_code.used = True
    await db.commit()

    # Get user
    user = await user_service.get_by_id(auth_code.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    # Build token claims
    scopes = auth_code.scope.split() if auth_code.scope else ["openid"]

    # Create access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "scope": auth_code.scope,
            "client_id": client.client_id,
        }
    )

    # Create refresh token
    raw_refresh, hashed_refresh = create_refresh_token(data={"sub": str(user.id)})
    refresh_record = RefreshToken(
        token_hash=hashed_refresh,
        user_id=user.id,
        client_id=client.id,
        scope=auth_code.scope,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_record)

    # Create ID token if openid scope
    id_token = None
    if "openid" in scopes:
        id_token_data = await _build_id_token_claims(
            user, scopes, client.client_id,
            team_service, permission_service, auth_code.nonce
        )
        id_token = create_id_token(
            data=id_token_data,
            nonce=auth_code.nonce,
        )

    await db.commit()

    # Log OAuth login activity
    await activity_service.log_login(
        user_id=user.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        oauth_client_id=client.id,
        oauth_client_name=client.name,
        login_method="oauth",
    )

    return OAuthTokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=raw_refresh,
        scope=auth_code.scope,
        id_token=id_token,
    )


async def _handle_refresh_token_grant(
    db: AsyncSession,
    client: OAuthClient,
    refresh_token_str: Optional[str],
    user_service: UserService,
) -> OAuthTokenResponse:
    """Handle refresh_token grant."""
    from sqlalchemy import select

    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required",
        )

    # Find refresh token
    token_hash = hash_token(refresh_token_str)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token_record = result.scalar_one_or_none()

    if not token_record or not token_record.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token",
        )

    if token_record.client_id != client.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client mismatch",
        )

    # Get user
    user = await user_service.get_by_id(token_record.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found or inactive",
        )

    # Revoke old token
    token_record.revoked = True

    # Create new tokens
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "scope": token_record.scope,
            "client_id": client.client_id,
        }
    )

    raw_refresh, hashed_refresh = create_refresh_token(data={"sub": str(user.id)})
    new_refresh = RefreshToken(
        token_hash=hashed_refresh,
        user_id=user.id,
        client_id=client.id,
        scope=token_record.scope,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_refresh)

    await db.commit()

    return OAuthTokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=raw_refresh,
        scope=token_record.scope,
    )


async def _build_id_token_claims(
    user: User,
    scopes: List[str],
    audience: str,
    team_service: TeamService,
    permission_service: PermissionService,
    nonce: Optional[str] = None,
) -> dict:
    """Build ID token claims based on scopes."""
    claims = {
        "sub": str(user.id),
        "aud": audience,
    }

    if "email" in scopes:
        claims["email"] = user.email
        claims["email_verified"] = True

    if "profile" in scopes:
        claims["given_name"] = user.first_name
        claims["family_name"] = user.last_name
        claims["name"] = user.full_name
        if user.avatar:
            claims["picture"] = user.avatar

    if "teams" in scopes:
        user_teams = await team_service.get_user_teams(user.id)
        claims["teams"] = [
            {"name": t.name, "slug": t.slug}
            for t in user_teams
        ]

    if "roles" in scopes:
        roles = []
        for team in await team_service.get_user_teams(user.id):
            member = await team_service.get_team_member(team.id, user.id)
            if member and member.role:
                roles.append({"name": member.role.name, "slug": member.role.slug})
        claims["roles"] = roles

    if "workspaces" in scopes:
        workspaces = await permission_service.get_user_workspaces(user.id)
        claims["workspaces"] = [
            {"name": w.name, "slug": w.slug}
            for w in workspaces
        ]

    if "permissions" in scopes:
        permissions = await permission_service.get_user_permissions(user.id)
        # Get permission details
        perm_list = []
        for slug in permissions:
            perm = await permission_service.get_permission_by_slug(slug)
            if perm:
                perm_list.append({"name": perm.name, "slug": perm.slug})
        claims["permissions"] = perm_list

    return claims


@router.get("/userinfo", response_model=UserInfoResponse)
async def userinfo(
    current_user: User = Depends(get_current_active_user),
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """OIDC UserInfo endpoint."""
    claims = await _build_id_token_claims(
        user=current_user,
        scopes=["openid", "profile", "email", "teams", "roles", "workspaces", "permissions"],
        audience="",
        team_service=team_service,
        permission_service=permission_service,
    )

    return UserInfoResponse(
        sub=claims["sub"],
        email=claims.get("email"),
        email_verified=True,
        given_name=claims.get("given_name"),
        family_name=claims.get("family_name"),
        name=claims.get("name"),
        picture=claims.get("picture"),
        teams=[TeamClaim(**t) for t in claims.get("teams", [])],
        roles=[RoleClaim(**r) for r in claims.get("roles", [])],
        workspaces=[WorkspaceClaim(**w) for w in claims.get("workspaces", [])],
        permissions=[PermissionClaim(**p) for p in claims.get("permissions", [])],
    )


@router.post("/revoke")
async def revoke_token(
    token: str = Form(...),
    token_type_hint: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a token."""
    from sqlalchemy import select, update

    # Try to revoke as refresh token
    token_hash = hash_token(token)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(revoked=True)
    )
    await db.commit()

    return {"message": "Token revoked"}
