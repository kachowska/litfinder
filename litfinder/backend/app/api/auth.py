"""
Auth API Endpoints
Registration, login, JWT tokens
"""
import logging
import uuid
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    revoke_refresh_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_MINUTES,
    DUMMY_PASSWORD_HASH
)

# Logger
logger = logging.getLogger(__name__)

router = APIRouter()


# --- Helper Functions ---

def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    # Check for at least one digit
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"

    # Check for at least one letter
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter"

    # Password is strong enough
    return True, None


# --- Schemas ---

class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (min 8 chars, must include letter and number)")
    name: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: dict


class UserResponse(BaseModel):
    """User info response."""
    id: str
    email: Optional[str]
    name: Optional[str]
    subscription_tier: str
    is_pro: bool


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class TelegramAuthRequest(BaseModel):
    """Telegram auth data."""
    telegram_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    auth_date: int
    hash: str


# --- Endpoints ---

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register new user with email and password.

    - Validates password strength (min 8 chars, letter + number required)
    - Checks if email already exists (case-insensitive)
    - Hashes password with bcrypt
    - Creates user record
    - Returns JWT access and refresh tokens
    """
    # Validate password strength
    is_valid, error_message = validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Normalize email to lowercase for case-insensitive comparison
    normalized_email = request.email.lower()

    # Check if email already exists (case-insensitive)
    result = await db.execute(
        select(User).where(
            func.lower(User.email) == normalized_email,
            User.deleted_at.is_(None)
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash password
    password_hash = hash_password(request.password)

    # Create user with normalized lowercase email
    user = User(
        id=uuid.uuid4(),
        email=normalized_email,
        name=request.name or normalized_email.split('@')[0],
        password_hash=password_hash,
        subscription_tier="free",
        search_limit_daily=10,
        searches_used_today=0,
        metadata_={}
    )

    db.add(user)

    # Handle race condition with IntegrityError
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Generate JWT tokens
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user.to_dict()
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login with email and password.

    - Verifies email and password (case-insensitive)
    - Returns JWT access token
    - Uses constant-time password verification to prevent timing attacks
    """
    # Normalize email to lowercase for case-insensitive comparison
    normalized_email = request.email.lower()

    # Get user by email (case-insensitive)
    result = await db.execute(
        select(User).where(
            func.lower(User.email) == normalized_email,
            User.deleted_at.is_(None)
        )
    )
    user = result.scalar_one_or_none()

    # Always perform password verification to prevent timing attacks
    # Use dummy hash if user doesn't exist or has no password
    if not user or not user.password_hash:
        # Perform dummy password verification to maintain constant time
        verify_password(request.password, DUMMY_PASSWORD_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Generate JWT tokens
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user.to_dict()
    )


@router.post("/logout")
async def logout(request: RefreshTokenRequest):
    """
    Logout by revoking refresh token.

    Idempotent operation - always succeeds even for malformed or already-revoked tokens.
    Client should remove tokens locally regardless of this endpoint's behavior.

    Args:
        request: Request containing refresh_token to revoke

    Returns:
        Always returns success response for fail-safe logout
    """
    # Validate token is present
    if not request.refresh_token:
        logger.warning("Logout attempted with empty refresh_token")
        # Still return success - logout is idempotent
        return {
            "status": "logged_out",
            "message": "Refresh token revoked. Access token should be removed client-side."
        }

    # Attempt to revoke the refresh token with fail-safe error handling
    try:
        await revoke_refresh_token(request.refresh_token)
        logger.info("Refresh token revoked successfully")
    except (ValueError, JWTError) as e:
        # Expected errors from malformed tokens
        # Log only exception type to avoid exposing token data
        logger.warning("Logout with invalid token (expected error): %s", type(e).__name__)
    except Exception as e:
        # Unexpected errors (Redis connection, etc.)
        logger.error(f"Unexpected error during token revocation: {type(e).__name__}: {str(e)}", exc_info=True)

    # Always return success - logout is idempotent and fail-safe
    return {
        "status": "logged_out",
        "message": "Refresh token revoked. Access token should be removed client-side."
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        subscription_tier=current_user.subscription_tier,
        is_pro=current_user.is_pro
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Refresh access token using refresh token.

    Implements token rotation for security:
    - Old refresh token is atomically revoked
    - New access + refresh tokens are issued
    - Prevents token replay attacks via atomic revocation

    Args:
        request: Request containing refresh_token

    Returns:
        New token pair (access + refresh tokens)

    Raises:
        401: If refresh token is invalid, expired, revoked, or already used
    """
    # Decode refresh token (checks expiration and revocation)
    payload = await decode_refresh_token(request.refresh_token)

    if payload is None:
        logger.warning("Refresh attempt with invalid/expired/revoked token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Extract user ID
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Convert user_id string to UUID for database query
    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_uuid, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning(f"Refresh token for non-existent or deleted user: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated"
        )

    # Atomically revoke the old refresh token (token rotation with race protection)
    # Returns True only if this request was first to claim the token
    token_claimed = await revoke_refresh_token(request.refresh_token)

    if not token_claimed:
        # Token was already used/revoked by another concurrent request
        # This prevents TOCTOU attacks where multiple requests race to rotate same token
        logger.warning(f"Token rotation race detected for user {user_id} - token already used")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token already used. Please login again."
        )

    # Generate new JWT tokens (only if we successfully claimed the old token)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    )

    logger.info(f"Successfully rotated tokens for user {user_id}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user.to_dict()
    )


@router.post("/telegram", response_model=TokenResponse)
async def telegram_auth(request: TelegramAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate via Telegram.

    TODO: Implement Telegram auth hash validation
    TODO: Create/update user based on Telegram data
    """
    raise HTTPException(status_code=501, detail="Telegram auth not implemented yet")
