"""
Bibliography Models
Lists and items for user's bibliography collections
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class BibliographyList(Base):
    """User's bibliography list/collection."""
    
    __tablename__ = "bibliography_lists"
    
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
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Formatting style
    style: Mapped[str] = mapped_column(String(50), default="GOST_R_7_0_100_2018")
    
    # Sharing
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    public_link: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    shared_with: Mapped[dict] = mapped_column(JSONB, default=list)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="bibliography_lists")
    items = relationship("BibliographyItem", back_populates="list", cascade="all, delete-orphan")


class BibliographyItem(Base):
    """Article in a bibliography list."""
    
    __tablename__ = "bibliography_items"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bibliography_lists.id", ondelete="CASCADE"),
        nullable=False
    )
    
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False
    )
    
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    list = relationship("BibliographyList", back_populates="items")
    article = relationship("Article")
