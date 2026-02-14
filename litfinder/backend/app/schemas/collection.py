"""
Pydantic schemas for Collections API.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, UUID4


# --- Collection Schemas ---

class CollectionBase(BaseModel):
    """Base collection schema with common fields."""
    title: str = Field(..., min_length=1, max_length=255, description="Collection title")
    description: Optional[str] = Field(None, description="Optional description")
    tags: List[str] = Field(default_factory=list, description="Collection tags")


class CollectionCreate(CollectionBase):
    """Schema for creating a new collection."""
    pass


class CollectionUpdate(BaseModel):
    """Schema for updating an existing collection. All fields optional."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class CollectionItemResponse(BaseModel):
    """Schema for collection item in response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    work_id: str
    notes: Optional[str]
    added_at: datetime


class CollectionResponse(CollectionBase):
    """Schema for collection in response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    items_count: int
    created_at: datetime
    updated_at: datetime


class CollectionDetailResponse(CollectionResponse):
    """Schema for detailed collection response with items."""
    model_config = ConfigDict(from_attributes=True)

    items: List[CollectionItemResponse] = []


# --- Collection Item Schemas ---

class CollectionItemAdd(BaseModel):
    """Schema for adding an item to a collection."""
    work_id: str = Field(..., description="OpenAlex work ID (e.g., 'W2741809807')")
    notes: Optional[str] = Field(None, description="Optional notes about this item")


class CollectionItemUpdate(BaseModel):
    """Schema for updating a collection item."""
    notes: Optional[str] = Field(None, description="Update notes")


# --- List Response Schemas ---

class CollectionListResponse(BaseModel):
    """Schema for paginated list of collections."""
    model_config = ConfigDict(from_attributes=True)

    collections: List[CollectionResponse]
    total: int
    page: int
    page_size: int
