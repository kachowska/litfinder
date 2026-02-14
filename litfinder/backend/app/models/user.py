"""
User Model
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class User(Base):
    """User entity."""
    
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Auth
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Subscription
    subscription_tier: Mapped[str] = mapped_column(String(20), default="free")  # free, pro, enterprise
    subscription_expires: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Usage limits
    search_limit_daily: Mapped[int] = mapped_column(Integer, default=10)
    searches_used_today: Mapped[int] = mapped_column(Integer, default=0)
    searches_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Settings
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)  # language, notifications, etc.
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)  # Soft delete
    
    # Relationships
    bibliography_lists = relationship("BibliographyList", back_populates="user", cascade="all, delete-orphan")
    search_history = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def is_pro(self) -> bool:
        """Check if user has Pro subscription."""
        if self.subscription_tier in ("pro", "enterprise"):
            if self.subscription_expires:
                return self.subscription_expires > datetime.utcnow()
        return False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "subscription_tier": self.subscription_tier,
            "is_pro": self.is_pro,
            "searches_used_today": self.searches_used_today,
            "search_limit_daily": self.search_limit_daily
        }
