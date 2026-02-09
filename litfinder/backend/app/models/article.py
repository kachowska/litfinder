"""
Article Model
Represents scientific articles from OpenAlex/CyberLeninka
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Text, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

from app.database import Base


class Article(Base):
    """Scientific article entity."""
    
    __tablename__ = "articles"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Source info
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # 'openalex', 'cyberleninka'
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Metadata
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[dict] = mapped_column(JSONB, default=list)  # [{name, initials}]
    year: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Publication info
    journal_name: Mapped[Optional[str]] = mapped_column(String(255))
    volume: Mapped[Optional[int]] = mapped_column(Integer)
    issue: Mapped[Optional[int]] = mapped_column(Integer)
    pages: Mapped[Optional[str]] = mapped_column(String(50))
    doi: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    
    # Content
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    abstract_snippet: Mapped[Optional[str]] = mapped_column(Text)
    pdf_url: Mapped[Optional[str]] = mapped_column(Text)
    
    # Classification
    concepts: Mapped[dict] = mapped_column(JSONB, default=list)  # [{id, name}]
    keywords: Mapped[dict] = mapped_column(JSONB, default=list)
    language: Mapped[str] = mapped_column(String(10), default="ru")
    
    # Metrics
    cited_by_count: Mapped[int] = mapped_column(Integer, default=0)
    open_access: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Vector embedding for semantic search
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    harvested_from: Mapped[str] = mapped_column(String(50), default="manual")
    
    __table_args__ = (
        Index('idx_articles_source_external', 'source', 'external_id', unique=True),
        Index('idx_articles_year', 'year'),
        Index('idx_articles_language', 'language'),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "source": self.source,
            "external_id": self.external_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal_name,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "doi": self.doi,
            "abstract": self.abstract,
            "abstract_snippet": self.abstract_snippet,
            "pdf_url": self.pdf_url,
            "concepts": self.concepts,
            "cited_by_count": self.cited_by_count,
            "open_access": self.open_access,
            "language": self.language
        }
