"""
User API Endpoints
Profile, history, settings
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.user import User
from app.models.collection import Collection, CollectionItem
from app.models.search_history import SearchHistory
from app.utils.security import get_current_user


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


class SearchHistoryResponse(BaseModel):
    """Search history response with pagination info."""
    total: int
    items: List[SearchHistoryItem]


class UsageStats(BaseModel):
    """User usage statistics."""
    searches_today: int
    searches_this_month: int
    lists_created: int
    articles_saved: int


# --- Endpoints ---

@router.get("/profile", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile."""
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        subscription_tier=current_user.subscription_tier,
        is_pro=current_user.is_pro,
        searches_used_today=current_user.searches_used_today,
        search_limit_daily=current_user.search_limit_daily
    )


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile."""
    # Update allowed fields
    if request.name is not None:
        current_user.name = request.name

    # Track if metadata was modified to mark it for SQLAlchemy
    metadata_modified = False

    # Initialize metadata dict if needed (once before updates)
    if request.language is not None or request.notifications is not None:
        if current_user.metadata_ is None:
            current_user.metadata_ = {}

    if request.language is not None:
        current_user.metadata_['language'] = request.language
        metadata_modified = True

    if request.notifications is not None:
        current_user.metadata_['notifications'] = request.notifications
        metadata_modified = True

    # Mark metadata as modified for SQLAlchemy to detect in-place changes
    if metadata_modified:
        flag_modified(current_user, "metadata_")

    await db.commit()
    await db.refresh(current_user)

    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        subscription_tier=current_user.subscription_tier,
        is_pro=current_user.is_pro,
        searches_used_today=current_user.searches_used_today,
        search_limit_daily=current_user.search_limit_daily
    )


@router.get("/searches", response_model=SearchHistoryResponse)
async def get_search_history(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's search history with pagination.

    Args:
        limit: Maximum number of results (default: 10, max: 100)
        offset: Number of results to skip (default: 0)

    Returns:
        SearchHistoryResponse with total count and paginated items
    """
    # Validate and cap limit
    limit = min(max(1, limit), 100)
    offset = max(0, offset)

    # Get total count
    count_result = await db.execute(
        select(func.count())
        .select_from(SearchHistory)
        .where(SearchHistory.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    # Query search history ordered by most recent
    result = await db.execute(
        select(SearchHistory)
        .where(SearchHistory.user_id == current_user.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    history_items = result.scalars().all()

    items = [
        SearchHistoryItem(
            id=str(item.id),
            query=item.query,
            results_count=item.results_count or 0,
            created_at=item.created_at.isoformat()
        )
        for item in history_items
    ]

    return SearchHistoryResponse(total=total, items=items)


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's usage statistics."""
    # Get searches today (from user model)
    searches_today = current_user.searches_used_today

    # Count searches this month from search history
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_searches_result = await db.execute(
        select(func.count(SearchHistory.id)).where(
            SearchHistory.user_id == current_user.id,
            SearchHistory.created_at >= month_start
        )
    )
    searches_this_month = month_searches_result.scalar() or 0

    # Count user's collections
    lists_count_result = await db.execute(
        select(func.count(Collection.id)).where(
            Collection.user_id == current_user.id
        )
    )
    lists_created = lists_count_result.scalar() or 0

    # Count total articles in user's collections
    articles_count_result = await db.execute(
        select(func.count(CollectionItem.id)).where(
            CollectionItem.collection_id.in_(
                select(Collection.id).where(
                    Collection.user_id == current_user.id
                )
            )
        )
    )
    articles_saved = articles_count_result.scalar() or 0

    return UsageStats(
        searches_today=searches_today,
        searches_this_month=searches_this_month,
        lists_created=lists_created,
        articles_saved=articles_saved
    )


@router.delete("/data")
async def delete_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete all user data (GDPR compliance).

    Performs complete data deletion in a single transaction:
    - Hard deletes all collections (cascade will delete items)
    - Hard deletes all search history
    - Soft deletes user account (sets deleted_at timestamp)

    This ensures:
    - User account data is marked as deleted
    - All collections and their items are permanently removed
    - All search history is permanently removed
    - Full GDPR right-to-erasure compliance
    """
    now = datetime.now(timezone.utc)

    # Hard delete all user's collections (cascade will delete items)
    # Bulk delete is more efficient than N+1 loop
    await db.execute(
        delete(Collection).where(Collection.user_id == current_user.id)
    )

    # Hard delete all user's search history (GDPR compliance)
    # Bulk delete is more efficient than N+1 loop
    await db.execute(
        delete(SearchHistory).where(SearchHistory.user_id == current_user.id)
    )

    # Soft delete user account
    current_user.deleted_at = now

    await db.commit()

    return {
        "status": "deleted",
        "message": "All user data has been deleted",
        "deleted_at": now.isoformat()
    }
