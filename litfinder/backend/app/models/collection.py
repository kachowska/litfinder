"""
Collection Models
User collections for organizing research papers
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.database import Base


class Collection(Base):
    """User collection for organizing papers."""

    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)

    # Timestamps (timezone-aware)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="collections")
    items = relationship(
        "CollectionItem",
        back_populates="collection",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def to_dict(self, include_items: bool = False) -> dict:
        """Convert to dictionary for API response."""
        result = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "description": self.description,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "items_count": len(self.items) if self.items else 0
        }

        if include_items and self.items:
            result["items"] = [item.to_dict() for item in self.items]

        return result


class CollectionItem(Base):
    """
    Item in a collection representing a reference to an OpenAlex work.

    Links to external OpenAlex works via the work_id field (e.g., "W2741809807")
    rather than storing a foreign key to local articles. This allows collections
    to reference any work from OpenAlex without requiring it to exist in our database.
    """

    __tablename__ = "collection_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False
    )

    work_id: Mapped[str] = mapped_column(String(255), nullable=False)  # OpenAlex work ID (e.g., "W2741809807")

    # User annotations
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamp (timezone-aware)
    added_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    collection = relationship("Collection", back_populates="items")

    __table_args__ = (
        Index(
            'idx_collection_items_collection_work',
            'collection_id',
            'work_id',
            unique=True
        ),
        Index('idx_collection_items_work_id', 'work_id'),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "collection_id": str(self.collection_id),
            "work_id": self.work_id,
            "notes": self.notes,
            "added_at": self.added_at.isoformat() if self.added_at else None
        }
