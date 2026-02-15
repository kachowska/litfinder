# GOST Bibliography Export Guide

## Overview

LitFinder provides comprehensive bibliography formatting and export capabilities according to **GOST R 7.0.100-2018** (Russian bibliographic standard). This is a key differentiator in the CIS market where GOST formatting is required for academic publications.

## Features

### Supported Standards

1. **GOST R 7.0.100-2018** - Main Russian bibliographic standard
2. **VAK** - Format for dissertations and theses

### Supported Source Types

- **Articles** - Journal publications
- **Books** - Monographs and textbooks
- **Conference Papers** - Conference proceedings
- **Electronic Resources** - Online publications
- **Theses** - Dissertations

### Export Formats

1. **GOST Text** (.txt) - Formatted bibliography list
2. **BibTeX** (.bib) - For LaTeX users
3. **RIS** (.ris) - For EndNote, Zotero, Mendeley
4. **Word** (.docx) - Microsoft Word document
5. **JSON** (.json) - Full metadata export
6. **CSV** (.csv) - Simple spreadsheet format

## API Endpoints

### 1. Preview Collection Bibliography

Get formatted preview before export:

```http
GET /api/v1/collections/{collection_id}/bibliography?sort_by=author&style=GOST_R_7_0_100_2018
```

**Query Parameters:**
- `sort_by` - Sort order: `author` (default), `year`, `title`
- `style` - Bibliography style: `GOST_R_7_0_100_2018` (default), `VAK`

**Response:**
```json
{
  "collection_id": "uuid",
  "title": "My Collection",
  "formatted_list": [
    "1. Иванов И. О. Название статьи / И. О. Иванов // Журнал. — 2024. — Т. 1. — № 2. — С. 10-20.",
    "2. Петров П. П. Другая статья..."
  ],
  "total": 2,
  "style": "GOST_R_7_0_100_2018",
  "sort_by": "author",
  "preview": true
}
```

### 2. Export Collection

Download collection in specified format:

```http
GET /api/v1/collections/{collection_id}/export/{format}?sort_by=author
```

**Path Parameters:**
- `format` - Export format: `gost`, `bibtex`, `ris`, `docx`, `json`, `csv`

**Query Parameters:**
- `sort_by` - Sort order: `author`, `year`, `title`

**Response:**
- File download with appropriate Content-Type
- Filename: `{collection_title}_{format}.{extension}`

### 3. Generate Bibliography

Generate bibliography from article list:

```http
POST /api/v1/bibliography
```

**Request Body:**
```json
{
  "articles": [
    {
      "title": "Machine Learning in Education",
      "authors": [
        {"name": "Smith John", "initials": "J."}
      ],
      "year": 2024,
      "journal_name": "Educational Technology",
      "volume": 15,
      "issue": 3,
      "pages": "45-60",
      "doi": "10.1234/example"
    }
  ],
  "style": "GOST_R_7_0_100_2018",
  "sort_by": "author",
  "numbered": true
}
```

**Response:**
```json
{
  "status": "success",
  "formatted_list": [
    "1. Smith J. Machine Learning in Education // Educational Technology. — 2024. — Т. 15. — № 3. — С. 45-60. — DOI: 10.1234/example."
  ],
  "bibtex": "@article{smith2024machine,\n  author = {Smith, J.},\n  ...\n}",
  "ris": "TY  - JOUR\nAU  - Smith, J.\n...",
  "validation": {
    "status": "success",
    "warnings": [],
    "errors": []
  },
  "metadata": {
    "total_sources": 1,
    "style": "GOST_R_7_0_100_2018",
    "sort_by": "author"
  }
}
```

## GOST Formatting Rules

### Article Format
```
Автор И. О. Название статьи / И. О. Автор, И. О. Соавтор // Журнал. — Год. — Т. vol. — № issue. — С. pages. — DOI: doi.
```

**Example:**
```
Иванов И. О. Применение машинного обучения в образовании / И. О. Иванов, П. П. Петров // Вестник науки. — 2024. — Т. 15. — № 3. — С. 45-60. — DOI: 10.1234/example.
```

### Book Format
```
Автор И. О. Название книги / И. О. Автор. — Город : Издательство, Год. — 123 с.
```

**Example:**
```
Смирнов С. С. Основы программирования / С. С. Смирнов. — Москва : Наука, 2024. — 350 с.
```

### Electronic Resource Format
```
Автор И. О. Название [Электронный ресурс] / И. О. Автор. — URL: url (дата обращения: dd.mm.yyyy).
```

**Example:**
```
Кузнецов К. К. Онлайн-курсы по искусственному интеллекту [Электронный ресурс] / К. К. Кузнецов. — URL: https://example.com (дата обращения: 14.02.2026).
```

## Usage Examples

### Export Collection as Word Document

```bash
curl -X GET "http://localhost:8000/api/v1/collections/{id}/export/docx?sort_by=year" \
  -H "Authorization: Bearer {token}" \
  --output bibliography.docx
```

### Preview GOST Formatting

```bash
curl -X GET "http://localhost:8000/api/v1/collections/{id}/bibliography?sort_by=author" \
  -H "Authorization: Bearer {token}"
```

### Export as BibTeX

```bash
curl -X GET "http://localhost:8000/api/v1/collections/{id}/export/bibtex" \
  -H "Authorization: Bearer {token}" \
  --output bibliography.bib
```

### Generate Custom Bibliography

```bash
curl -X POST "http://localhost:8000/api/v1/bibliography" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "articles": [...],
    "style": "GOST_R_7_0_100_2018",
    "sort_by": "author"
  }'
```

## Sort Options

### By Author (Alphabetical)
Articles sorted by first author's last name (default):
```
1. Алексеев А. А. ...
2. Борисов Б. Б. ...
3. Васильев В. В. ...
```

### By Year (Newest First)
Articles sorted by publication year (descending):
```
1. Автор (2024) ...
2. Автор (2023) ...
3. Автор (2022) ...
```

### By Title (Alphabetical)
Articles sorted by title:
```
1. Анализ данных ...
2. Базы данных ...
3. Визуализация ...
```

## Word Export Features

The `.docx` export includes:

- **Proper margins:** 2cm left, 1.5cm right, 2cm top/bottom
- **Font:** Times New Roman, 14pt
- **Formatting:** Hanging indent (1cm)
- **Spacing:** 6pt after each entry
- **Centered title:** "Список литературы"
- **Numbered list:** Automatic numbering

## Validation

The bibliography generator performs automatic validation:

### Warnings
- Missing authors
- Missing publication year
- Incomplete citation data

### Errors
- Invalid article format
- Parsing failures
- Empty article list

### Example Response with Validation
```json
{
  "status": "success",
  "formatted_list": [...],
  "validation": {
    "status": "warning",
    "warnings": [
      "Missing authors: Machine Learning Basics",
      "Missing year: Deep Learning Introduction"
    ],
    "errors": []
  }
}
```

## Integration with Collections

### Workflow

1. **Create Collection**
   ```http
   POST /api/v1/collections
   {
     "title": "AI Research Papers",
     "description": "Collection for dissertation"
   }
   ```

2. **Add Articles**
   ```http
   POST /api/v1/collections/{id}/items
   {
     "work_id": "W2741809807",
     "notes": "Key paper for chapter 2"
   }
   ```

3. **Preview Bibliography**
   ```http
   GET /api/v1/collections/{id}/bibliography
   ```

4. **Export in GOST Format**
   ```http
   GET /api/v1/collections/{id}/export/docx
   ```

## Best Practices

### 1. Check Preview First
Always preview before exporting to verify formatting:
```javascript
// Frontend example
const preview = await fetch(`/api/v1/collections/${id}/bibliography`);
// Show preview to user
// Then allow export
```

### 2. Choose Appropriate Format
- **Word (.docx)** - For direct use in academic writing
- **BibTeX (.bib)** - For LaTeX users
- **RIS (.ris)** - For reference managers (Zotero, Mendeley)
- **JSON (.json)** - For backup and data processing

### 3. Sort Strategically
- **Alphabetical (author)** - Most common for bibliographies
- **Chronological (year)** - For literature reviews
- **By title** - For alphabetical indexes

### 4. Validate Before Export
Check validation warnings and fix missing data:
```python
# Example: Add missing years
for article in articles:
    if not article.get('year'):
        article['year'] = 2024  # or fetch from source
```

## Error Handling

### Empty Collection
```json
{
  "status": 400,
  "detail": "Collection is empty"
}
```

### Unsupported Format
```json
{
  "status": 400,
  "detail": "Unsupported export format: pdf. Supported: gost, bibtex, ris, docx, json, csv"
}
```

### Collection Not Found
```json
{
  "status": 404,
  "detail": "Collection not found"
}
```

## Performance Considerations

### Batch Size
- Small collections (<50 items): Instant export
- Medium collections (50-200 items): 1-2 seconds
- Large collections (200-500 items): 3-5 seconds

### Caching
- Bibliography formatting results are not cached
- Fresh formatting on each request (ensures up-to-date data)

### Rate Limits
- Export endpoints follow standard API rate limits
- Free tier: 10 exports/hour
- Pro tier: 1000 exports/hour

## Future Enhancements

Planned for future versions:

1. **VAK Standard** - Full support for VAK dissertation requirements
2. **Custom Styles** - User-defined formatting rules
3. **Batch Export** - Export multiple collections at once
4. **Templates** - Customizable Word templates
5. **Citations** - In-text citation generation
6. **Language Detection** - Automatic Cyrillic/Latin formatting

## Support

For issues or questions:
- Documentation: `/help`
- GitHub: https://github.com/anthropics/litfinder/issues
- Email: support@litfinder.ai

---

**Note:** GOST R 7.0.100-2018 is the current Russian standard for bibliographic description. This implementation follows the official standard with minor adaptations for digital sources.
