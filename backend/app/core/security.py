"""
Security utilities for authentication and authorization.
Includes password hashing, JWT token handling, and PKCE validation.
"""

import hashlib
import secrets
import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Cache for JWT keys
_private_key: Optional[str] = None
_public_key: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Hash a token using SHA-256 for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def _load_or_generate_keys() -> tuple[str, str]:
    """Load JWT keys from file/config or generate new ones."""
    global _private_key, _public_key

    if _private_key and _public_key:
        return _private_key, _public_key

    # Try loading from direct config
    if settings.JWT_PRIVATE_KEY and settings.JWT_PUBLIC_KEY:
        _private_key = settings.JWT_PRIVATE_KEY
        _public_key = settings.JWT_PUBLIC_KEY
        return _private_key, _public_key

    # Try loading from file paths
    if settings.JWT_PRIVATE_KEY_PATH and settings.JWT_PUBLIC_KEY_PATH:
        private_path = Path(settings.JWT_PRIVATE_KEY_PATH)
        public_path = Path(settings.JWT_PUBLIC_KEY_PATH)

        if private_path.exists() and public_path.exists():
            _private_key = private_path.read_text()
            _public_key = public_path.read_text()
            return _private_key, _public_key

    # Generate new RSA key pair for development
    if settings.is_development:
        private_key_obj = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        _private_key = private_key_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

        _public_key = private_key_obj.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        return _private_key, _public_key

    raise ValueError(
        "JWT keys not configured. Set JWT_PRIVATE_KEY and JWT_PUBLIC_KEY "
        "or JWT_PRIVATE_KEY_PATH and JWT_PUBLIC_KEY_PATH in environment."
    )


def get_private_key() -> str:
    """Get the private key for signing tokens."""
    private_key, _ = _load_or_generate_keys()
    return private_key


def get_public_key() -> str:
    """Get the public key for verifying tokens."""
    _, public_key = _load_or_generate_keys()
    return public_key


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    })

    private_key = get_private_key()
    return jwt.encode(to_encode, private_key, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, str]:
    """
    Create a refresh token.

    Returns:
        Tuple of (raw_token, hashed_token) - raw for client, hash for storage
    """
    raw_token = generate_secure_token(48)
    hashed_token = hash_token(raw_token)

    return raw_token, hashed_token


def create_id_token(
    data: dict[str, Any],
    nonce: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create an OIDC ID token with identity claims.

    Args:
        data: User identity data
        nonce: Optional nonce from authorization request
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT ID token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=1)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "auth_time": int(datetime.now(timezone.utc).timestamp()),
        "iss": settings.BACKEND_URL,
    })

    if nonce:
        to_encode["nonce"] = nonce

    private_key = get_private_key()
    return jwt.encode(to_encode, private_key, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload or None if invalid
    """
    try:
        public_key = get_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        return payload
    except JWTError:
        return None


def verify_code_challenge(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """
    Verify PKCE code challenge.

    Args:
        code_verifier: The original code verifier from token request
        code_challenge: The stored code challenge from authorization request
        method: Challenge method ('S256' or 'plain')

    Returns:
        True if verification succeeds
    """
    if method == "plain":
        return code_verifier == code_challenge

    if method == "S256":
        # SHA-256 hash then base64url encode
        computed = hashlib.sha256(code_verifier.encode("ascii")).digest()
        computed_challenge = base64.urlsafe_b64encode(computed).rstrip(b"=").decode("ascii")
        return computed_challenge == code_challenge

    return False


def generate_client_credentials() -> tuple[str, str]:
    """
    Generate OAuth client credentials.

    Returns:
        Tuple of (client_id, client_secret)
    """
    client_id = f"tc_{secrets.token_hex(16)}"
    client_secret = secrets.token_urlsafe(32)
    return client_id, client_secret
