"""
GOST Р 7.0.100-2018 Bibliography Formatter
Russian standard for bibliographic references.

Formats:
- Books: Автор И. О. Название / И. О. Автор. — Город : Издательство, Год. — С. pages.
- Articles: Автор И. О. Название статьи // Журнал. — Год. — Т. vol. — № issue. — С. pages.
- Electronic: Автор И. О. Название [Электронный ресурс]. — URL: url (дата обращения: dd.mm.yyyy).
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class SourceType(Enum):
    """Type of bibliographic source."""
    BOOK = "book"
    ARTICLE = "article"
    CONFERENCE = "conference"
    THESIS = "thesis"
    ELECTRONIC = "electronic"
    PATENT = "patent"
    STANDARD = "standard"


@dataclass
class Author:
    """Author representation."""
    last_name: str
    initials: str = ""
    first_name: str = ""
    middle_name: str = ""
    
    def format_gost(self) -> str:
        """Format author for GOST: Фамилия И. О."""
        if self.initials:
            return f"{self.last_name} {self.initials}"
        
        parts = []
        if self.first_name:
            parts.append(f"{self.first_name[0]}.")
        if self.middle_name:
            parts.append(f"{self.middle_name[0]}.")
        
        initials = " ".join(parts) if parts else ""
        return f"{self.last_name} {initials}".strip()
    
    def format_gost_inverted(self) -> str:
        """Format author inverted for responsibility: И. О. Фамилия"""
        if self.initials:
            return f"{self.initials} {self.last_name}"
        
        parts = []
        if self.first_name:
            parts.append(f"{self.first_name[0]}.")
        if self.middle_name:
            parts.append(f"{self.middle_name[0]}.")
        
        initials = " ".join(parts) if parts else ""
        return f"{initials} {self.last_name}".strip()


@dataclass 
class BibliographyEntry:
    """Complete bibliographic entry."""
    title: str
    authors: List[Author]
    year: Optional[int] = None
    source_type: SourceType = SourceType.ARTICLE
    
    # Journal/conference
    journal_name: Optional[str] = None
    volume: Optional[int] = None
    issue: Optional[int] = None
    pages: Optional[str] = None
    
    # Book
    publisher: Optional[str] = None
    city: Optional[str] = None
    total_pages: Optional[int] = None
    edition: Optional[str] = None
    
    # Electronic
    url: Optional[str] = None
    doi: Optional[str] = None
    access_date: Optional[datetime] = None
    
    # Conference
    conference_name: Optional[str] = None
    conference_location: Optional[str] = None
    conference_date: Optional[str] = None


class GOSTFormatter:
    """Format bibliographic entries according to GOST Р 7.0.100-2018."""
    
    def format(self, entry: BibliographyEntry) -> str:
        """Format entry according to its type."""
        formatters = {
            SourceType.BOOK: self._format_book,
            SourceType.ARTICLE: self._format_article,
            SourceType.CONFERENCE: self._format_conference,
            SourceType.ELECTRONIC: self._format_electronic,
            SourceType.THESIS: self._format_thesis,
        }
        
        formatter = formatters.get(entry.source_type, self._format_article)
        return formatter(entry)
    
    def format_list(
        self, 
        entries: List[BibliographyEntry],
        sort_by: str = "author"
    ) -> List[str]:
        """Format and sort list of entries."""
        # Sort entries
        if sort_by == "author":
            entries = sorted(entries, key=lambda e: e.authors[0].last_name if e.authors else "")
        elif sort_by == "year":
            entries = sorted(entries, key=lambda e: e.year or 0, reverse=True)
        elif sort_by == "title":
            entries = sorted(entries, key=lambda e: e.title)
        
        # Format with numbering
        formatted = []
        for i, entry in enumerate(entries, 1):
            formatted.append(f"{i}. {self.format(entry)}")
        
        return formatted
    
    def _format_authors(self, authors: List[Author], max_authors: int = 3) -> str:
        """Format author list for GOST."""
        if not authors:
            return ""
        
        if len(authors) == 1:
            return authors[0].format_gost()
        
        # First author only in main position
        first = authors[0].format_gost()
        
        return first
    
    def _format_responsibility(self, authors: List[Author]) -> str:
        """Format responsibility zone (after /)."""
        if not authors:
            return ""
        
        if len(authors) <= 3:
            names = [a.format_gost_inverted() for a in authors]
            return ", ".join(names)
        else:
            # More than 3 authors: first 3 + [и др.]
            names = [a.format_gost_inverted() for a in authors[:3]]
            return ", ".join(names) + " [и др.]"
    
    def _format_article(self, entry: BibliographyEntry) -> str:
        """
        Format journal article:
        Автор И. О. Название статьи / И. О. Автор, И. О. Соавтор // Журнал. — Год. — Т. vol. — № issue. — С. pages.
        """
        parts = []
        
        # Author and title
        author = self._format_authors(entry.authors)
        if author:
            parts.append(f"{author}.")
        
        parts.append(entry.title)
        
        # Responsibility zone
        responsibility = self._format_responsibility(entry.authors)
        if responsibility and len(entry.authors) > 1:
            parts.append(f"/ {responsibility}")
        
        # Journal
        if entry.journal_name:
            parts.append(f"// {entry.journal_name}.")
        
        # Year
        if entry.year:
            parts.append(f"— {entry.year}.")
        
        # Volume
        if entry.volume:
            parts.append(f"— Т. {entry.volume}.")
        
        # Issue
        if entry.issue:
            parts.append(f"— № {entry.issue}.")
        
        # Pages
        if entry.pages:
            parts.append(f"— С. {entry.pages}.")
        
        # DOI
        if entry.doi:
            parts.append(f"— DOI: {entry.doi}.")
        
        return " ".join(parts)
    
    def _format_book(self, entry: BibliographyEntry) -> str:
        """
        Format book:
        Автор И. О. Название книги / И. О. Автор. — Город : Издательство, Год. — 123 с.
        """
        parts = []
        
        # Author and title
        author = self._format_authors(entry.authors)
        if author:
            parts.append(f"{author}.")
        
        parts.append(entry.title)
        
        # Responsibility
        responsibility = self._format_responsibility(entry.authors)
        if responsibility:
            parts.append(f"/ {responsibility}.")
        
        # Edition
        if entry.edition:
            parts.append(f"— {entry.edition}.")
        
        # City and publisher
        city = entry.city or "Б.м."  # Без места
        publisher = entry.publisher or "б.и."  # без издателя
        year = entry.year or "б.г."  # без года
        parts.append(f"— {city} : {publisher}, {year}.")
        
        # Pages
        if entry.total_pages:
            parts.append(f"— {entry.total_pages} с.")
        
        # DOI
        if entry.doi:
            parts.append(f"— DOI: {entry.doi}.")
        
        return " ".join(parts)
    
    def _format_conference(self, entry: BibliographyEntry) -> str:
        """
        Format conference paper:
        Автор И. О. Название / И. О. Автор // Название конференции. — Город, Год. — С. pages.
        """
        parts = []
        
        # Author and title
        author = self._format_authors(entry.authors)
        if author:
            parts.append(f"{author}.")
        
        parts.append(entry.title)
        
        # Responsibility
        responsibility = self._format_responsibility(entry.authors)
        if responsibility and len(entry.authors) > 1:
            parts.append(f"/ {responsibility}")
        
        # Conference
        if entry.conference_name:
            parts.append(f"// {entry.conference_name}.")
        
        # Location and year
        location_parts = []
        if entry.conference_location:
            location_parts.append(entry.conference_location)
        if entry.year:
            location_parts.append(str(entry.year))
        if location_parts:
            parts.append(f"— {', '.join(location_parts)}.")
        
        # Pages
        if entry.pages:
            parts.append(f"— С. {entry.pages}.")
        
        return " ".join(parts)
    
    def _format_electronic(self, entry: BibliographyEntry) -> str:
        """
        Format electronic resource:
        Автор И. О. Название [Электронный ресурс] / И. О. Автор. — URL: url (дата обращения: dd.mm.yyyy).
        """
        parts = []
        
        # Author and title
        author = self._format_authors(entry.authors)
        if author:
            parts.append(f"{author}.")
        
        parts.append(f"{entry.title} [Электронный ресурс]")
        
        # Responsibility
        responsibility = self._format_responsibility(entry.authors)
        if responsibility:
            parts.append(f"/ {responsibility}.")
        
        # URL
        if entry.url:
            access_date = entry.access_date or datetime.now()
            date_str = access_date.strftime("%d.%m.%Y")
            parts.append(f"— URL: {entry.url} (дата обращения: {date_str}).")
        elif entry.doi:
            access_date = entry.access_date or datetime.now()
            date_str = access_date.strftime("%d.%m.%Y")
            parts.append(f"— DOI: {entry.doi} (дата обращения: {date_str}).")
        
        return " ".join(parts)
    
    def _format_thesis(self, entry: BibliographyEntry) -> str:
        """Format thesis/dissertation."""
        parts = []
        
        author = self._format_authors(entry.authors)
        if author:
            parts.append(f"{author}.")
        
        parts.append(entry.title)
        parts.append(": дис. ... канд./д-ра наук")
        
        # Responsibility
        responsibility = self._format_responsibility(entry.authors)
        if responsibility:
            parts.append(f"/ {responsibility}.")
        
        # City and year
        city = entry.city or "Б.м."
        year = entry.year or "б.г."
        parts.append(f"— {city}, {year}.")
        
        if entry.total_pages:
            parts.append(f"— {entry.total_pages} с.")
        
        return " ".join(parts)


# --- Helper functions ---

def article_to_bibliography_entry(article: dict) -> BibliographyEntry:
    """Convert article dict to BibliographyEntry."""
    # Parse authors
    authors = []
    for a in article.get("authors", []):
        if isinstance(a, dict):
            name = a.get("name", "")
            parts = name.split()
            if parts:
                last_name = parts[0]
                initials = a.get("initials", "")
                if not initials and len(parts) > 1:
                    initials = " ".join(p[0] + "." for p in parts[1:] if p)
                authors.append(Author(last_name=last_name, initials=initials))
    
    # Determine source type
    source_type = SourceType.ARTICLE
    if article.get("url") and not article.get("journal_name"):
        source_type = SourceType.ELECTRONIC
    elif article.get("conference_name"):
        source_type = SourceType.CONFERENCE
    
    return BibliographyEntry(
        title=article.get("title", ""),
        authors=authors,
        year=article.get("year"),
        source_type=source_type,
        journal_name=article.get("journal_name") or article.get("journal"),
        volume=article.get("volume"),
        issue=article.get("issue"),
        pages=article.get("pages"),
        url=article.get("pdf_url") or article.get("url"),
        doi=article.get("doi"),
        access_date=datetime.now()
    )


# --- Singleton instance ---
gost_formatter = GOSTFormatter()
