"""
Collections API endpoints.

Provides CRUD operations for user collections and collection items.
Uses work_id (OpenAlex ID string) instead of foreign keys to articles.
"""
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.user import User
from app.models.collection import Collection, CollectionItem
from app.utils.security import get_current_user

# Import schemas from the new schemas/collection.py file
# For now, define them inline since we just created that file
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Schemas (inline for now) ---

class CollectionCreate(BaseModel):
    """Schema for creating a new collection."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)


class CollectionUpdate(BaseModel):
    """Schema for updating an existing collection."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class CollectionItemAdd(BaseModel):
    """Schema for adding an item to a collection."""
    work_id: str = Field(..., description="OpenAlex work ID (e.g., 'W2741809807')")
    notes: Optional[str] = None


class CollectionItemUpdate(BaseModel):
    """Schema for updating a collection item."""
    notes: Optional[str] = None


class CollectionItemResponse(BaseModel):
    """Schema for collection item in response."""
    id: str
    collection_id: str
    work_id: str
    notes: Optional[str]
    added_at: datetime

    class Config:
        from_attributes = True


class CollectionResponse(BaseModel):
    """Schema for collection in response."""
    id: str
    user_id: str
    title: str
    description: Optional[str]
    tags: List[str]
    items_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectionDetailResponse(CollectionResponse):
    """Schema for detailed collection response with items."""
    items: List[CollectionItemResponse] = []


class CollectionListResponse(BaseModel):
    """Schema for paginated list of collections."""
    collections: List[CollectionResponse]
    total: int
    page: int
    page_size: int


# --- Collection CRUD Operations ---

@router.post("/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection_data: CollectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new collection.

    - **title**: Collection title (required)
    - **description**: Optional description
    - **tags**: Optional list of tags
    """
    new_collection = Collection(
        user_id=current_user.id,
        title=collection_data.title,
        description=collection_data.description,
        tags=collection_data.tags or []
    )

    db.add(new_collection)
    await db.commit()
    await db.refresh(new_collection)

    logger.info(f"Created collection {new_collection.id} for user {current_user.id}")

    return CollectionResponse(
        id=str(new_collection.id),
        user_id=str(new_collection.user_id),
        title=new_collection.title,
        description=new_collection.description,
        tags=new_collection.tags or [],
        items_count=0,
        created_at=new_collection.created_at,
        updated_at=new_collection.updated_at
    )


@router.get("/", response_model=CollectionListResponse)
async def list_collections(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all collections for the current user.

    Supports pagination:
    - **page**: Page number (starts at 1)
    - **page_size**: Items per page (max 100)
    """
    # Get total count
    count_query = select(func.count()).select_from(Collection).where(
        Collection.user_id == current_user.id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get collections (without loading items)
    offset = (page - 1) * page_size

    query = (
        select(Collection)
        .where(Collection.user_id == current_user.id)
        .order_by(Collection.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    collections = result.scalars().all()

    # Get item counts for these collections using aggregation (efficient)
    collection_ids = [c.id for c in collections]

    if collection_ids:
        # Run aggregated count query: SELECT collection_id, COUNT(*) GROUP BY collection_id
        count_query = (
            select(CollectionItem.collection_id, func.count())
            .where(CollectionItem.collection_id.in_(collection_ids))
            .group_by(CollectionItem.collection_id)
        )
        count_result = await db.execute(count_query)
        # Build mapping: collection_id -> item_count
        items_count_map = {coll_id: count for coll_id, count in count_result}
    else:
        items_count_map = {}

    # Convert to response format using aggregated counts
    collection_responses = [
        CollectionResponse(
            id=str(c.id),
            user_id=str(c.user_id),
            title=c.title,
            description=c.description,
            tags=c.tags or [],
            items_count=items_count_map.get(c.id, 0),  # Lookup count from map
            created_at=c.created_at,
            updated_at=c.updated_at
        )
        for c in collections
    ]

    return CollectionListResponse(
        collections=collection_responses,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{collection_id}", response_model=CollectionDetailResponse)
async def get_collection(
    collection_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific collection with all its items.

    Returns 404 if collection doesn't exist or doesn't belong to user.
    """
    query = (
        select(Collection)
        .where(
            and_(
                Collection.id == collection_id,
                Collection.user_id == current_user.id
            )
        )
        .options(selectinload(Collection.items))
    )

    result = await db.execute(query)
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    # Convert items to response format
    item_responses = [
        CollectionItemResponse(
            id=str(item.id),
            collection_id=str(item.collection_id),
            work_id=item.work_id,
            notes=item.notes,
            added_at=item.added_at
        )
        for item in (collection.items or [])
    ]

    return CollectionDetailResponse(
        id=str(collection.id),
        user_id=str(collection.user_id),
        title=collection.title,
        description=collection.description,
        tags=collection.tags or [],
        items_count=len(item_responses),
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        items=item_responses
    )


@router.patch("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: UUID,
    collection_update: CollectionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a collection's metadata.

    Only updates fields that are provided. All fields are optional.
    """
    query = (
        select(Collection)
        .where(
            and_(
                Collection.id == collection_id,
                Collection.user_id == current_user.id
            )
        )
    )

    result = await db.execute(query)
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    # Update only fields that were explicitly provided in the request
    # Using exclude_unset=True distinguishes "not sent" from "sent as null"
    update_data = collection_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(collection, field, value)

    await db.commit()
    await db.refresh(collection)

    # Get item count efficiently without loading all items
    count_query = select(func.count()).select_from(CollectionItem).where(
        CollectionItem.collection_id == collection_id
    )
    count_result = await db.execute(count_query)
    items_count = count_result.scalar_one()

    logger.info(f"Updated collection {collection_id}")

    return CollectionResponse(
        id=str(collection.id),
        user_id=str(collection.user_id),
        title=collection.title,
        description=collection.description,
        tags=collection.tags or [],
        items_count=items_count,
        created_at=collection.created_at,
        updated_at=collection.updated_at
    )


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a collection and all its items.

    This operation is irreversible.
    """
    query = select(Collection).where(
        and_(
            Collection.id == collection_id,
            Collection.user_id == current_user.id
        )
    )

    result = await db.execute(query)
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    await db.delete(collection)
    await db.commit()

    logger.info(f"Deleted collection {collection_id}")

    return None


# --- Collection Item Operations ---

@router.post("/{collection_id}/items", response_model=CollectionItemResponse, status_code=status.HTTP_201_CREATED)
async def add_item_to_collection(
    collection_id: UUID,
    item_data: CollectionItemAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add an article (work) to a collection.

    - **work_id**: OpenAlex work ID (e.g., "W2741809807")
    - **notes**: Optional notes about this item

    Returns 409 if the item is already in the collection.
    """
    # Verify collection exists and belongs to user
    query = select(Collection).where(
        and_(
            Collection.id == collection_id,
            Collection.user_id == current_user.id
        )
    )

    result = await db.execute(query)
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    # Create new item
    new_item = CollectionItem(
        collection_id=collection_id,
        work_id=item_data.work_id,
        notes=item_data.notes
    )

    db.add(new_item)

    try:
        await db.commit()
        await db.refresh(new_item)
    except IntegrityError as e:
        await db.rollback()

        # Check if this is specifically the duplicate work constraint violation
        # PostgreSQL unique_violation error code is '23505'
        # Our constraint name is 'idx_collection_items_collection_work'
        error_info = str(e.orig) if hasattr(e, 'orig') else str(e)

        # Check for our specific unique constraint
        if (hasattr(e.orig, 'pgcode') and e.orig.pgcode == '23505' and
            'idx_collection_items_collection_work' in error_info):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This work is already in the collection"
            )

        # For other integrity errors (foreign key, check constraints, etc.),
        # log the actual error for debugging but return generic message to client
        logger.error(f"Integrity error adding item to collection {collection_id}: {error_info}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to add item to collection. Please check that the collection exists and try again."
        )

    logger.info(f"Added work {item_data.work_id} to collection {collection_id}")

    return CollectionItemResponse(
        id=str(new_item.id),
        collection_id=str(new_item.collection_id),
        work_id=new_item.work_id,
        notes=new_item.notes,
        added_at=new_item.added_at
    )


@router.patch("/{collection_id}/items/{work_id}", response_model=CollectionItemResponse)
async def update_collection_item(
    collection_id: UUID,
    work_id: str,
    item_update: CollectionItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update notes for a collection item.
    """
    # Verify collection exists and belongs to user
    collection_query = select(Collection).where(
        and_(
            Collection.id == collection_id,
            Collection.user_id == current_user.id
        )
    )

    collection_result = await db.execute(collection_query)
    collection = collection_result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    # Fetch item
    item_query = select(CollectionItem).where(
        and_(
            CollectionItem.collection_id == collection_id,
            CollectionItem.work_id == work_id
        )
    )

    item_result = await db.execute(item_query)
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in collection"
        )

    # Update only fields that were explicitly provided in the request
    # Using exclude_unset=True distinguishes "not sent" from "sent as null"
    update_data = item_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)

    logger.info(f"Updated item {work_id} in collection {collection_id}")

    return CollectionItemResponse(
        id=str(item.id),
        collection_id=str(item.collection_id),
        work_id=item.work_id,
        notes=item.notes,
        added_at=item.added_at
    )


@router.delete("/{collection_id}/items/{work_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_collection(
    collection_id: UUID,
    work_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove an article from a collection.
    """
    # Verify collection exists and belongs to user
    collection_query = select(Collection).where(
        and_(
            Collection.id == collection_id,
            Collection.user_id == current_user.id
        )
    )

    collection_result = await db.execute(collection_query)
    collection = collection_result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    # Fetch and delete item
    item_query = select(CollectionItem).where(
        and_(
            CollectionItem.collection_id == collection_id,
            CollectionItem.work_id == work_id
        )
    )

    item_result = await db.execute(item_query)
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in collection"
        )

    await db.delete(item)
    await db.commit()

    logger.info(f"Removed work {work_id} from collection {collection_id}")

    return None
