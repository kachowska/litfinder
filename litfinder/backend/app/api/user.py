"""
User API Endpoints
Profile, history, settings
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


router = APIRouter()


# --- Schemas ---

class UserProfile(BaseModel):
    """User profile response."""
    id: str
    email: Optional[str]
    name: Optional[str]
    subscription_tier: str
    is_pro: bool
    searches_used_today: int
    search_limit_daily: int


class UpdateProfileRequest(BaseModel):
    """Update profile request."""
    name: Optional[str] = None
    language: Optional[str] = None
    notifications: Optional[bool] = None


class SearchHistoryItem(BaseModel):
    """Search history item."""
    id: str
    query: str
    results_count: int
    created_at: str


class UsageStats(BaseModel):
    """User usage statistics."""
    searches_today: int
    searches_this_month: int
    lists_created: int
    articles_saved: int


# --- Endpoints ---

@router.get("/profile", response_model=UserProfile)
async def get_profile(db: AsyncSession = Depends(get_db)):
    """Get current user profile."""
    # TODO: Get from JWT token
    raise HTTPException(status_code=401, detail="Not authenticated")


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    request: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update user profile."""
    raise HTTPException(status_code=401, detail="Not authenticated")


@router.get("/searches", response_model=List[SearchHistoryItem])
async def get_search_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get user's search history."""
    # TODO: Paginated history
    return []


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(db: AsyncSession = Depends(get_db)):
    """Get user's usage statistics."""
    return UsageStats(
        searches_today=0,
        searches_this_month=0,
        lists_created=0,
        articles_saved=0
    )


@router.delete("/data")
async def delete_user_data(db: AsyncSession = Depends(get_db)):
    """Delete all user data (GDPR compliance)."""
    # TODO: Implement data deletion
    raise HTTPException(status_code=401, detail="Not authenticated")
