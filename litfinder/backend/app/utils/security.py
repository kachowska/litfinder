"""
Security Utilities
JWT token generation and password hashing
"""
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.user import User

# Logger
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT security
security = HTTPBearer()

# JWT settings (from config)
SECRET_KEY = settings.jwt_secret_key or settings.secret_key  # Fallback to secret_key for backward compatibility
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_MINUTES = settings.refresh_token_expire_minutes

# Dummy password hash for timing attack prevention
# This is a bcrypt hash of "dummy_password_for_timing_attack_prevention"
# Used to ensure constant-time password verification even when user doesn't exist
DUMMY_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU0qpXuP.9BO"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token.

    Args:
        data: Payload to encode (e.g., {"sub": user_id})
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    # Use timezone-aware datetime (Python 3.12+ deprecates utcnow)
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token with unique JWT ID (jti) for revocation tracking.

    Args:
        data: Payload to encode (e.g., {"sub": user_id})
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()

    # Use timezone-aware datetime (Python 3.12+ deprecates utcnow)
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    # Generate unique JWT ID for revocation tracking
    jti = str(uuid.uuid4())

    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": jti
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Verify token type
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


async def is_token_revoked(jti: str) -> bool:
    """
    Check if a refresh token has been revoked.

    On cache errors, defaults to fail-closed (returns True) for security.
    This prevents revoked tokens from being accepted when Redis is down.
    Can be configured via FAIL_CLOSED_ON_CACHE_ERROR env var.

    Args:
        jti: JWT ID to check

    Returns:
        True if token is revoked (or cache check failed with fail-closed)
        False if token is not revoked
    """
    from app.services.cache_service import cache_service

    try:
        # Check if jti exists in revoked tokens store
        return await cache_service.exists(f"revoked_token:{jti}")
    except Exception as e:
        # Log the error with jti for observability
        logger.error(
            f"Cache error checking token revocation for jti={jti}: {type(e).__name__}: {str(e)}",
            exc_info=True
        )

        # Fail-closed by default (secure): treat token as revoked on cache errors
        # This prevents accepting revoked tokens when Redis is down
        if settings.fail_closed_on_cache_error:
            logger.warning(
                f"Failing closed due to cache error - treating token as revoked (jti={jti})"
            )
            return True  # Fail-closed: reject token
        else:
            logger.warning(
                f"Failing open due to cache error - treating token as valid (jti={jti})"
            )
            return False  # Fail-open: allow token (insecure, for testing only)


async def revoke_refresh_token(token: str) -> bool:
    """
    Atomically revoke a refresh token by storing its jti in Redis.

    Uses SETNX (set-if-not-exists) to ensure only one request can claim
    a token for rotation, preventing TOCTOU race conditions.

    Args:
        token: JWT refresh token string to revoke

    Returns:
        True if this was the first revocation (token was claimed atomically)
        False if token was already revoked or invalid
    """
    from app.services.cache_service import cache_service

    try:
        # Decode without expiration validation so we can parse expired tokens
        # We'll manually check expiration below for TTL calculation
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False}
        )
        jti = payload.get("jti")
        exp = payload.get("exp")

        if not jti:
            return False

        # Calculate TTL from token expiration
        if exp:
            ttl_seconds = exp - int(time.time())
            if ttl_seconds <= 0:
                # Token already expired, no need to revoke
                # Return False to prevent rotation of expired tokens
                return False
            ttl = timedelta(seconds=ttl_seconds)
        else:
            # Default TTL if no expiration
            ttl = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

        # Atomically store jti using SETNX - only succeeds if key doesn't exist
        # This ensures only ONE concurrent request can claim this token
        claimed = await cache_service.set_if_not_exists(
            f"revoked_token:{jti}",
            "revoked",
            ttl
        )

        # Return True only if we were first to claim (atomic operation succeeded)
        return claimed

    except Exception as e:
        # Log with full exception context and stacktrace
        logger.error(
            f"Token revocation error: {type(e).__name__}: {str(e)}",
            exc_info=True
        )
        return False


async def decode_refresh_token(token: str) -> Optional[dict]:
    """
    Decode and validate JWT refresh token, checking revocation status.

    Args:
        token: JWT refresh token string

    Returns:
        Decoded payload or None if invalid or revoked
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Verify token type
        if payload.get("type") != "refresh":
            return None

        # Check if token has been revoked
        jti = payload.get("jti")
        if jti and await is_token_revoked(jti):
            return None

        return payload

    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization header with Bearer token
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    # Extract user ID
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Convert user_id string to UUID for database query
    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise credentials_exception

    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_uuid, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user
