# LitFinder MVP: Comprehensive Implementation Plan
**Version:** 1.0 MVP
**Date:** February 13, 2026
**Status:** In Progress (Week 1/8 completed)
**Target:** Complete Elicit.com backend clone for CIS market

---

## Executive Summary

LitFinder is an AI-powered platform for scientific literature research targeting the CIS market (Russia, Kazakhstan, Belarus). This document provides a comprehensive roadmap to implement **all 8 core features** from the specification, tracking what's completed, what's pending, and the phases needed to reach first demo.

**Key Differentiators:**
- Native VAK RB and GOST R 7.0.100-2018 formatting support
- Multilingual (Russian + English)
- Modern AI stack (Claude 4.x, OpenAI embeddings)
- Affordable: ~$1/user/month operational cost

---

## 1. Feature Inventory & Implementation Status

### Core Features Overview

| # | Feature | Elicit Equivalent | Status | Priority | Completion |
|---|---------|------------------|--------|----------|-----------|
| 1 | Research Assistant (RAG) | Elicit AI Search | ✅ **DONE** | P0 | 100% |
| 2 | Table Data Extraction | Elicit Extract | ❌ Not Started | P0 | 0% |
| 3 | Chat with Library | Elicit Chat with Papers | ❌ Not Started | P0 | 0% |
| 4 | Systematic Review Workflow | Elicit Review Pipeline | ❌ Not Started | P1 | 0% |
| 5 | Concept Map | Elicit Concepts Tool | ❌ Not Started | P1 | 0% |
| 6 | Alerts & Monitoring | Elicit Alerts, Scite Dashboards | ❌ Not Started | P2 | 0% |
| 7 | Reference Check | Scite Reference Check | ❌ Not Started | P2 | 0% |
| 8 | GOST Formatter | **Unique to LitFinder** | ❌ Not Started | P0 | 0% |

### Foundation Features (Required for all)

| Feature | Description | Status | Completion |
|---------|-------------|--------|-----------|
| Authentication | JWT-based auth (register/login/refresh) | ⏳ Partial | 80% |
| OpenAlex Integration | Search API integration | ⏳ Partial | 70% |
| Collections Management | CRUD operations for user collections | ❌ Not Started | 0% |
| Database Schema | PostgreSQL schema with pgvector | ✅ **DONE** | 100% |
| Vector Embeddings | Gemini text-embedding-004 (768-dim) | ✅ **DONE** | 100% |
| LLM Service | Claude 4.x integration with task routing | ✅ **DONE** | 100% |
| Cache Service | Redis caching layer | ✅ **DONE** | 100% |
| Frontend | Next.js 14 + React 18 + TailwindCSS | ❌ Not Started | 0% |

---

## 2. Detailed Feature Status

### ✅ Feature 1: Research Assistant (RAG) - **COMPLETE**

**What Elicit Has:**
- Semantic search with AI-powered answer synthesis
- Citation tracking with [N] format
- Filters (year, language, document type)
- Response streaming (for better UX)

**What We Implemented:**
- ✅ POST /api/v1/research/answer endpoint
- ✅ Vector similarity search (pgvector + HNSW index)
- ✅ Query embedding generation (Gemini text-embedding-004)
- ✅ Answer synthesis with Claude Sonnet 4
- ✅ Citation parsing ([1], [1,2], [1-3] formats)
- ✅ Redis caching (1 hour TTL, schema versioning)
- ✅ Filters: year_from, year_to, language, max_results
- ✅ Security: SQL injection prevention, defensive author handling
- ✅ Concurrent HNSW index creation (zero-downtime)
- ✅ Embedding generation script (backfill existing articles)

**What We Haven't Done:**
- ❌ Response streaming (planned Week 5)
- ❌ Query expansion/reformulation
- ❌ Hybrid search (vector + BM25 keyword search)
- ❌ Re-ranking with Haiku
- ❌ Multi-hop reasoning

**Files:**
- `backend/app/api/research.py` (main implementation)
- `backend/alembic/versions/003_add_vector_index.py` (HNSW index)
- `backend/app/scripts/generate_embeddings.py` (backfill script)
- `FEATURE_1_RESEARCH_ASSISTANT.md` (documentation)

**Performance:**
- Current: P95 ~6s, P50 ~3s (MVP baseline)
- Target: P95 ≤3s, P50 ~2s (after 4-week optimization roadmap)

---

### ❌ Feature 2: Table Data Extraction - **NOT STARTED**

**What Elicit Has:**
- Extract structured data from papers (sample size, methodology, main finding)
- Custom field definitions
- Interactive table with sorting/filtering
- CSV/Excel export
- Progress tracking for batch extraction
- Tooltips with source quotes

**What We Need to Implement:**

**Backend Components:**
1. **Extraction Jobs Management**
   - POST /api/v1/extraction/jobs
   - Schema: ExtractionJob (user_id, collection_id, fields: JSONB, status, created_at, completed_at)
   - Database table: `extraction_jobs`

2. **Field-based Extraction Pipeline**
   - Iterate through articles in collection
   - For each article + field definition:
     - Build context (title, abstract, full-text if available)
     - LLM extraction (Claude Haiku for speed)
     - Parse structured response (field_name, value, quote, confidence)
   - Store in `extraction_results` table

3. **Progress Tracking**
   - WebSocket or SSE for real-time updates
   - Status: pending → processing → completed/failed

4. **Export Functionality**
   - GET /api/v1/extraction/jobs/{id}/export?format=csv
   - Formats: CSV, Excel (.xlsx)

**UI Components (Frontend):**
- Modal "Data Extraction" from collection context menu
- Form to define fields (name + description + type: numeric/text/categorical)
- Progress bar with "Processed N/M papers"
- Interactive results table (sortable, filterable)
- Hover tooltips showing source quotes
- Export buttons (CSV/Excel)

**LLM Configuration:**
- Model: Claude Haiku 4.5 (fast, cheap)
- Temperature: 0.2 (factual)
- Max tokens: 800
- Prompt: Structured extraction with field definitions

**Success Metrics:**
- ≥75% extraction accuracy (expert validation)
- P95 ≤30s for 20 papers
- ≥30% of collections use extraction
- ≥60% of completed extractions are exported

**Estimated Effort:** 3-4 days (Week 5-6)

---

### ❌ Feature 3: Chat with Library (Conversational RAG) - **NOT STARTED**

**What Elicit Has:**
- Chat with papers in a collection
- Compare methodologies/results across papers
- Get summaries and conclusions
- Find contradictions between papers
- Persistent conversation history
- Clickable source citations [ID]

**What We Need to Implement:**

**Backend Components:**
1. **Document Chunking & Indexing**
   - When articles added to collection → chunk asynchronously
   - Chunk size: 512 tokens, overlap: 50 tokens
   - Generate embedding for each chunk
   - Store in `collection_chunks` table (collection_id, work_id, chunk_text, embedding)

2. **Chat Session Management**
   - POST /api/v1/chat/collection
   - Schema: ChatSession (id, collection_id, user_id, messages: List[ChatMessage], created_at)
   - Database tables: `chat_sessions`, `chat_messages`

3. **Semantic Retrieval**
   - Generate query embedding
   - Vector similarity search in `collection_chunks` (pgvector)
   - Retrieve top-10 relevant chunks

4. **Conversational LLM**
   - Model: Claude Sonnet 4
   - Temperature: 0.4 (balanced)
   - Max tokens: 1500
   - Context: Last 5 messages + retrieved chunks
   - System prompt: "You're a research assistant helping with a library of papers. Answer ONLY using the provided context. Cite sources using [ID] notation. Point out contradictions if they exist."

5. **Session Persistence**
   - Store each message with role (user/assistant), content, sources_used

**UI Components:**
- "Chat" tab within collection screen
- Chat interface: input box at bottom, message history above
- Messages with citations: clickable [ID] → opens source in sidebar
- Sidebar: list of papers used in current session
- Quick prompts: "What methods are used?", "Compare results"

**Performance Optimization:**
- Chunking: async on collection update (background job)
- pgvector indexes: <100ms similarity search
- History limit: last 5 messages (context window management)
- Rate limiting: 20 messages/hour for free tier

**Success Metrics:**
- ≥40% of collections users initiate a chat session
- Average ≥3 messages per session
- P95 response time ≤5s
- User satisfaction ≥4.2/5.0

**Estimated Effort:** 4-5 days (Week 5-6)

---

### ❌ Feature 4: Systematic Review Workflow (State Machine) - **NOT STARTED**

**What Elicit Has:**
- Structured workflow: Import → Screening → Full-text review → Extraction → Completed
- AI-assisted screening recommendations (include/exclude/uncertain)
- Batch processing with keyboard shortcuts (I, E, Space)
- Progress tracking and statistics
- Export final included/excluded lists

**What We Need to Implement:**

**Backend Components:**
1. **Review Management**
   - Schema: Review (id, user_id, title, research_question, inclusion_criteria, exclusion_criteria, status: ReviewStatus, created_at)
   - ReviewStatus enum: SETUP, SCREENING, FULL_TEXT, EXTRACTION, COMPLETED

2. **Review Items Tracking**
   - Schema: ReviewItem (id, review_id, work_id, status: undecided/include/exclude, screening_notes, ai_recommendation, decided_by, decided_at)
   - Initially all items are "undecided"

3. **AI-Assisted Screening**
   - Model: Claude Haiku 4.5
   - Input: work (title, authors, year, abstract) + review criteria
   - Output: JSON with recommendation (include/exclude/uncertain), reasoning, matched_criteria, confidence (0.0-1.0)
   - Endpoint: GET /api/v1/reviews/{id}/items/next?batch_size=20

4. **Batch Screening**
   - Fetch undecided items in batches of 20
   - Parallel AI recommendation generation
   - Return items with AI suggestions

5. **Review Statistics**
   - GET /api/v1/reviews/{id}/stats
   - Returns: total_items, screened, included, excluded, undecided, ai_agree_rate

**UI Components:**
- /reviews page with list of user's reviews
- Create review form: title, research question, inclusion/exclusion criteria
- Screening workspace:
  - Current paper card (title, abstract, AI recommendation with reasoning)
  - Buttons: "Include" (I), "Exclude" (E), "Skip" (Space)
  - Keyboard shortcuts
  - Progress bar: "Screened 15/200"
- Final export: list of included papers (60 items)

**Success Metrics:**
- ≥20% of users create at least 1 review
- Average screening time <30s per paper
- AI agreement rate ≥65% (when user agrees with AI recommendation)
- Completion rate ≥40% (reviews that reach COMPLETED status)

**Estimated Effort:** 3-4 days (Week 7)

---

### ❌ Feature 5: Concept Map (Knowledge Graph Visualization) - **NOT STARTED**

**What Elicit Has:**
- Automatic concept map generation for a research area
- Key concepts with links between them
- Representative papers for each concept
- Recommendations to expand search
- Interactive graph visualization

**What We Need to Implement:**

**Backend Components:**
1. **Concept Extraction**
   - Input: topic query (e.g., "machine learning in education")
   - Search OpenAlex for top 50 papers (year_from=2019)
   - Extract OpenAlex concepts (level 1-2)
   - Create work summaries (first 30 papers)

2. **LLM Clustering**
   - Model: Claude Sonnet 4
   - Input: topic + base concepts + work summaries
   - Prompt: "Analyze this research area and create a conceptual map with 5-10 main concepts. For each concept: name (2-4 words), description (1 sentence), 2-3 subconcepts, links to other concepts."
   - Output: JSON with ConceptMap structure

3. **Visual Graph Generation**
   - Schema: ConceptGraph (nodes: List[ConceptNode], edges: List[ConceptEdge])
   - ConceptNode: id, label, description, size (by paper count), color (by category)
   - ConceptEdge: source, target, strength (relationship intensity)

**UI Components:**
- /concepts page with topic search input
- Interactive graph (react-force-graph or vis.js)
- Sidebar: selected concept details + 5 key papers
- List of representative papers below graph
- Button: "Search papers by concept" → transition to search with concept filter

**Key Interactions:**
1. User enters "Machine learning in education"
2. System generates map with 8 concepts
3. User clicks on "Personalized learning systems"
4. Sidebar shows description + 5 papers
5. User clicks "Search papers" → goes to search filtered by this concept
6. Adds papers to collection "Adaptive learning"

**Success Metrics:**
- ≥30% of new users try concept map
- ≥50% click on concepts and view papers
- ≥25% transition from concept map to search
- P95 generation time ≤15s

**Estimated Effort:** 2-3 days (Week 7)

---

### ❌ Feature 6: Alerts & Monitoring (Publication Notifications) - **NOT STARTED**

**What Elicit Has:**
- Automatic notifications for new relevant papers
- Alert types: saved searches, review themes, paper citations
- Frequency: daily, weekly
- Channels: email, Telegram
- Alert history with archive

**What We Need to Implement:**

**Backend Components:**
1. **Alert Configuration**
   - Schema: Alert (id, user_id, type: search/review/citations, query, review_id, collection_id, frequency: daily/weekly, channel: email/telegram, last_checked, is_active)
   - Endpoint: POST /api/v1/alerts

2. **Daily Alert Processing (Cron Job)**
   - Runs daily at 9:00 UTC
   - Fetch active alerts with frequency='daily' and last_checked < NOW() - INTERVAL '23 hours'
   - For each alert:
     - Check for new papers (check_alert logic)
     - If new papers found → send notification
     - Update last_checked timestamp

3. **Alert Checking Logic**
   - **Search alerts:** Check OpenAlex from yesterday's date (from_publication_date=yesterday)
   - **Review alerts:** Check new papers matching review criteria
   - **Citation alerts:** Check new citations for papers in collection
   - Filter by relevance score >0.7 (LLM-based relevance check with Haiku)
   - Return top-5 most relevant papers

4. **Notification Delivery**
   - **Email:** HTML template with paper list (title, authors, year, abstract snippet)
   - **Telegram:** Send message to user's telegram_chat_id with formatted paper list
   - Use async queues (Celery or FastAPI BackgroundTasks)

**UI Components:**
- /alerts page with list of active alerts
- Create alert: from search results or review
- Settings: frequency (daily/weekly), channel (email/Telegram)
- Alert history: archive of found papers with timestamps

**Key Interactions:**
1. User performs search "Quantum computing"
2. Clicks "Create alert for this query"
3. Selects Telegram, daily frequency
4. Next day: receives Telegram message with 3 new papers
5. Clicks link → opens paper on platform
6. Adds to collection

**Success Metrics:**
- ≥25% of active users create at least 1 alert
- Email open rate ≥40%
- Click-through rate ≥15%
- Average 2-3 alerts per user

**Estimated Effort:** 3-4 days (Week 8+, post-MVP)

---

### ❌ Feature 7: Reference Check (Citation Suggestion) - **NOT STARTED**

**What Scite Has:**
- Analyze draft text to identify claims needing citations
- Find relevant sources to support claims
- Check for contradictions with existing literature
- Prioritize claims by importance (high/medium/low)

**What We Need to Implement:**

**Backend Components:**
1. **Claim Extraction**
   - Endpoint: POST /api/v1/reference-check
   - Input: text (up to 10,000 characters), language: ru/en
   - Model: Claude Sonnet 4
   - Prompt: "Analyze this academic text and extract claims that require citations. For each claim, specify: text, type (fact/statistic/conclusion/method), priority (high/medium/low), start/end position."
   - Output: List[Claim] with JSON structure

2. **Source Matching**
   - For each claim:
     - Search OpenAlex with claim text (limit=10)
     - LLM evaluation (Claude Haiku): "Does this source support the claim?"
     - Output: SourceMatch with relevance (0.0-1.0), support_type (strong/partial/contradicts/unrelated), excerpt (quote from paper abstract)
   - Return top-3 sources per claim

3. **Aggregation**
   - Schema: ReferenceCheckResult (claims: List[ClaimWithSources], summary: ReferenceCheckSummary)
   - Summary: total_claims, high_priority count, sources_found, gaps (claims without good sources)

**UI Components:**
- /reference-check page with text area
- Paste or upload .docx file
- Highlighted claims in text (color by priority: red=high, yellow=medium, gray=low)
- Sidebar: found sources for selected claim
- Hover over source → preview with relevant quote
- Buttons: "Add to collection", "Copy quote"

**Key Interactions:**
1. User pastes dissertation fragment (3 paragraphs)
2. Clicks "Check"
3. 8 claims highlighted (4 high priority)
4. Clicks on first high-priority claim
5. Sidebar shows 3 matching sources
6. Hovers over source #1 → sees relevant quote
7. Adds source to collection
8. Copies formatted quote for insertion

**Success Metrics:**
- ≥35% of users try the function
- ≥60% add at least 1 found source to collection
- Extraction accuracy ≥80% (claims correctly identified)
- Source relevance (user rating) ≥3.8/5.0

**Estimated Effort:** 3-4 days (Week 8+, post-MVP)

---

### ❌ Feature 8: GOST Formatter (Unique to LitFinder) - **NOT STARTED**

**What LitFinder Needs (Unique Differentiator):**
- Format bibliographic entries according to:
  - **GOST R 7.0.100-2018** (Russia, Kazakhstan)
  - **VAK RB** (Belarus)
- Export to: BibTeX, RIS, JSON, .docx, .txt
- Batch formatting for entire collections
- Preview before export
- Warnings for missing/low-confidence data

**What We Need to Implement:**

**Backend Components:**
1. **GOST Formatter API Integration**
   - External service: GOST Formatter Agent (Claude Haiku 4.5)
   - Endpoint: POST {GOST_FORMATTER_URL}/api/v1/format/bibliography
   - Input: source_data (normalized article metadata), format_style (VAK_RB/GOST_R), output_language: ru, return_bibtex: true
   - Output: formatted_text, bibtex, confidence, warnings

2. **Batch Formatting**
   - Endpoint: POST /api/v1/format/batch
   - Input: collection_id, style (VAK_RB/GOST_R), numbering: bool
   - Process:
     - Fetch all articles from collection (ORDER BY added_at)
     - Normalize metadata (map Article fields → GOST format)
     - Format in parallel (batches of 10)
     - Add numbering if requested
   - Output: BatchFormatResult with formatted_items

3. **Export Formats**
   - Endpoint: GET /api/v1/format/export?collection_id=...&format=docx
   - Formats:
     - **docx:** Generate .docx with numbered list
     - **txt:** Plain text file
     - **json:** Formatted items as JSON array
     - **bibtex:** BibTeX entries

**UI Components:**
- Button "Format" in collection screen
- Modal to select standard: VAK RB or GOST R
- Preview: 60 entries shown, 2 warnings highlighted
- Check entries with warnings → fix metadata
- Buttons: "Export to Word", "Export as BibTeX", "Copy to clipboard"

**Key Interactions:**
1. User opens collection with 60 sources
2. Clicks "Format as VAK RB"
3. Sees preview with 60 entries (2 warnings about missing issue numbers)
4. Checks entries with warnings, fixes metadata
5. Clicks "Export to Word"
6. Downloads ready .docx file with formatted bibliography

**Success Metrics:**
- ≥70% of users with collections format them
- ≥90% formatting accuracy (by expert evaluation)
- P95 formatting time ≤3s for 10 papers
- ≥80% export results

**Estimated Effort:** 2-3 days (Week 3-4)

---

## 3. Foundation Features Status

### Authentication & Authorization

**What Elicit Has:**
- Email/password registration and login
- OAuth2 (Google, GitHub, etc.)
- Session management
- API key generation for programmatic access

**What We Have:**
- ⏳ JWT tokens (access + refresh) - **80% complete**
- ⏳ Bcrypt password hashing - **Done**
- ⏳ OAuth2 flow with password grant - **Done**
- ❌ OAuth2 providers (Google, GitHub) - **Not Started**
- ❌ Email verification - **Not Started**
- ❌ Password reset flow - **Not Started**

**Endpoints:**
- ✅ POST /api/v1/auth/register
- ✅ POST /api/v1/auth/login
- ✅ POST /api/v1/auth/refresh
- ❌ POST /api/v1/auth/verify-email
- ❌ POST /api/v1/auth/reset-password

**Missing for MVP:**
- Email verification (can use simple email/password for MVP)
- OAuth2 providers (nice-to-have, not blocking)

**Estimated Effort:** 1 day to polish (Week 2)

---

### Collections Management

**What Elicit Has:**
- Create/read/update/delete collections
- Add/remove articles from collections
- Tags and descriptions
- Sharing and collaboration (Phase 2)

**What We Need:**
- ❌ Database schema for `collections` and `collection_items` tables
- ❌ CRUD endpoints
- ❌ Permission checks (users can only access their own collections)

**Database Schema:**
```sql
CREATE TABLE collections (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE collection_items (
    id UUID PRIMARY KEY,
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    work_id TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    INDEX idx_collection_work (collection_id, work_id)
);
```

**Endpoints:**
- POST /api/v1/collections (create collection)
- GET /api/v1/collections (list user's collections)
- GET /api/v1/collections/{id} (get collection with items)
- PATCH /api/v1/collections/{id} (update title/description/tags)
- DELETE /api/v1/collections/{id} (delete collection)
- POST /api/v1/collections/{id}/items (add article to collection)
- DELETE /api/v1/collections/{id}/items/{work_id} (remove article)

**Estimated Effort:** 2 days (Week 3)

---

### OpenAlex Integration

**What We Have:**
- ⏳ Basic search integration - **70% complete**
- ⏳ Article metadata fetching - **Done**
- ⏳ Filters: year, type, language, open_access - **Partial**

**What We Need:**
- ❌ Cursor-based pagination for deep paging
- ❌ More advanced filters (cited_by_count, concepts)
- ❌ Bulk article fetching (for collections)

**Endpoint:**
- ✅ GET /api/v1/search/works (exists but needs polish)

**Estimated Effort:** 1 day to polish (Week 2)

---

### Frontend (Next.js + React)

**What Elicit Has:**
- Modern, clean UI with search-first design
- Responsive layout
- Real-time updates (streaming responses)
- Rich interactions (drag-and-drop, keyboard shortcuts)

**What We Need:**
- ❌ Complete frontend application - **0% started**
- ❌ Pages: /, /search, /collections, /collections/{id}, /research, /chat, /reviews, /concepts, /alerts, /reference-check, /format
- ❌ Components: SearchBar, ArticleCard, CollectionList, ChatInterface, etc.
- ❌ State management (React Context or Zustand)
- ❌ API client with authentication
- ❌ Tailwind UI components

**Tech Stack:**
- Next.js 14 (App Router)
- React 18
- TailwindCSS
- TypeScript
- Axios or Fetch for API calls
- React Query for data fetching
- Shadcn/UI or Headless UI for components

**Estimated Effort:** 7-10 days (Week 7 + ongoing)

---

## 4. Development Phases to First Demo

### Phase 0: Foundation (Week 1-2) - **IN PROGRESS**

**Goal:** Complete core infrastructure and basic functionality

**Tasks:**
- [x] Database schema setup (users, articles with pgvector)
- [x] JWT authentication implementation
- [x] OpenAlex integration (basic search)
- [x] LLM service setup (Claude integration)
- [x] Cache service setup (Redis)
- [x] Vector embedding service (Gemini)
- [x] Feature 1: Research Assistant (RAG) - **COMPLETE**
- [ ] Polish authentication (email verification optional for MVP)
- [ ] Polish OpenAlex integration (cursor pagination)
- [ ] Collections CRUD backend implementation
- [ ] Basic API health check and monitoring setup

**Deliverables:**
- ✅ Working Research Assistant endpoint
- ⏳ Complete auth system (missing email verification)
- ⏳ Collections backend ready
- ⏳ All services containerized and running

**Current Status:** ~70% complete (Week 1.5/2)

---

### Phase 1: Collections + GOST (Week 3-4)

**Goal:** Implement collections management and unique GOST formatting feature

**Tasks:**
- [ ] Collections CRUD endpoints (2 days)
- [ ] GOST Formatter integration (2 days)
  - Integrate external GOST Formatter API
  - Implement batch formatting
  - Add export functionality (.docx, .txt, BibTeX, JSON)
- [ ] Collection export endpoint (1 day)
  - CSV export (simple)
  - JSON export (full metadata)
- [ ] Testing and bug fixes (1 day)

**Deliverables:**
- Working collections management
- GOST formatting (VAK RB + GOST R)
- Export functionality

**Demo Capability:** Users can create collections, add papers, and export formatted bibliographies in GOST format

---

### Phase 2: Core AI Features (Week 5-6)

**Goal:** Implement the 3 most critical AI features for MVP

**Priority Order:**
1. **Feature 2: Table Data Extraction** (3-4 days)
   - Highest user value for systematic reviews
   - Differentiator vs generic tools
2. **Feature 3: Chat with Library** (4-5 days)
   - High engagement feature
   - Leverages existing RAG infrastructure
3. **Research Assistant Optimization** (2 days)
   - Add response streaming
   - Improve performance (caching, parallel processing)

**Tasks:**
- [ ] Implement data extraction pipeline
  - Extraction jobs management
  - Field-based LLM extraction (Haiku)
  - Progress tracking
  - Results storage
- [ ] Implement chat with library
  - Document chunking on collection update
  - Chat session management
  - Semantic retrieval from chunks
  - Conversational LLM with source citations
- [ ] Add response streaming to Research Assistant
- [ ] Performance optimization (P95 from ~6s to ~4s)

**Deliverables:**
- Working data extraction for collections
- Interactive chat with library
- Improved Research Assistant performance

**Demo Capability:** Users can extract structured data from papers and have conversations with their library

---

### Phase 3: Review Workflow + Concept Map (Week 7)

**Goal:** Implement systematic review support and concept mapping

**Tasks:**
- [ ] Feature 4: Systematic Review Workflow (3-4 days)
  - Review management (CRUD)
  - Review items tracking
  - AI-assisted screening (Haiku recommendations)
  - Batch screening with statistics
- [ ] Feature 5: Concept Map (2-3 days)
  - Concept extraction from topic
  - LLM clustering (Sonnet)
  - Graph generation
- [ ] Frontend development kickoff (2-3 days)
  - Project setup (Next.js + TypeScript + Tailwind)
  - Basic layout and navigation
  - Authentication pages
  - Search page skeleton

**Deliverables:**
- Working systematic review workflow
- Concept map generation
- Frontend project structure

**Demo Capability:** Users can conduct systematic reviews with AI assistance and explore research areas via concept maps

---

### Phase 4: Frontend MVP (Week 8)

**Goal:** Build minimal frontend to connect all backend features

**Tasks:**
- [ ] Core pages implementation (5 days)
  - Home page with search
  - Search results page
  - Collection management page
  - Research Assistant interface
  - Chat interface
  - Data extraction interface
  - Review workflow interface
- [ ] API integration (2 days)
  - Authentication flow
  - API client with token management
  - Error handling
- [ ] Testing and polish (1 day)
  - Integration testing
  - UI/UX refinements
  - Bug fixes

**Deliverables:**
- Complete frontend MVP
- End-to-end user flows working
- All Phase 0-3 features accessible via UI

**Demo Capability:** **FIRST COMPLETE DEMO READY**
- Users can register, search papers, create collections
- Use Research Assistant for AI-powered answers
- Extract structured data from papers
- Chat with their library
- Conduct systematic reviews
- Explore concept maps
- Format bibliographies in GOST

---

### Phase 5: Post-MVP (Week 9+)

**What We're Deferring:**
- ❌ Feature 6: Alerts & Monitoring (Week 9-10)
- ❌ Feature 7: Reference Check (Week 11-12)
- ❌ Email verification for auth
- ❌ OAuth2 providers (Google, GitHub)
- ❌ Advanced search features (hybrid search, re-ranking)
- ❌ Response streaming optimization
- ❌ Mobile app
- ❌ Collaboration features

These features are valuable but not blocking for first demo. They will be implemented in 4-week sprints after MVP launch.

---

## 5. Current Sprint (Week 1-2 Completion)

### Immediate Tasks (Next 3 Days)

**Priority 1: Complete Foundation** ⏰ **DUE: Week 2 End**

- [ ] **Task 1.1:** Polish authentication system (0.5 day)
  - Fix any remaining bugs in JWT refresh flow
  - Add proper error messages
  - Test password hashing edge cases
  - Document auth endpoints

- [ ] **Task 1.2:** Complete OpenAlex integration (0.5 day)
  - Add cursor-based pagination for deep paging
  - Add more filters (cited_by_count, concepts, is_oa)
  - Test edge cases (no results, API errors)
  - Add retry logic for API failures

- [ ] **Task 1.3:** Implement Collections CRUD (2 days)
  - Create database migration for collections + collection_items tables
  - Implement all CRUD endpoints
  - Add permission checks (users can only access their own collections)
  - Write unit tests
  - Test with real data

**Success Criteria:**
- ✅ Auth system has 100% test coverage
- ✅ OpenAlex pagination works for >100 results
- ✅ Users can create collections and add/remove articles
- ✅ All endpoints return proper error messages
- ✅ API documentation updated

---

## 6. Success Metrics & KPIs

### MVP Success Metrics (First 3 Months)

**Product Metrics:**
- ≥100 registered users
- ≥30 active users (weekly)
- ≥50 created collections
- ≥1,000 articles added to collections
- Retention rate (D7) ≥30%

**Feature Adoption:**
- Research Answer: ≥50% of users try it
- Data Extraction: ≥20% use it
- Chat with Library: ≥30% use it
- GOST Formatting: ≥60% use it (unique value prop)

**Performance:**
- Research Answer: P95 ≤4s (baseline ~6s, target ~3s after optimization)
- Data Extraction: P95 ≤30s for 20 papers
- Chat with Library: P95 ≤5s per message
- API uptime: ≥99.5%

**User Satisfaction:**
- NPS (Net Promoter Score): ≥40
- CSAT (Customer Satisfaction): ≥4.0/5.0
- Feature usefulness rating: ≥4.2/5.0

### Cost Targets

**Monthly Operating Cost (1000 active users):**
- LLM APIs: $659
- Infrastructure (Yandex Cloud): $280
- Domain/SSL: $10
- External services: $50
- **Total:** ~$1,000/month ($12,000/year)
- **Cost per user:** ~$1.00/month

**Cost Optimization Strategies:**
- Use Haiku for fast tasks (extraction, screening) → 90% cheaper than Sonnet
- Aggressive caching (1-hour TTL for research answers)
- Prompt optimization (reduce input tokens by 30%)
- Batch processing where possible

---

## 7. Technical Risks & Mitigation

### High-Priority Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **LLM API rate limits** | High | High | Rate limiting, queues, batch processing, fallback to cheaper models |
| **High LLM costs** | High | High | Prompt optimization, caching, freemium model with usage limits |
| **Slow performance** | Medium | High | Async processing, caching, CDN, connection pooling |
| **Low quality LLM responses** | Medium | Medium | Confidence thresholds, validation, user feedback loops |
| **OpenAlex API unavailability** | Medium | Medium | Caching, fallback to Semantic Scholar API |

### Medium-Priority Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Low user adoption** | Medium | High | Pilot with university aspirants (BGU), iterations based on feedback |
| **Competition from Elicit/Scite** | Low | Medium | Focus on CIS market differentiation (VAK/GOST), Russian language support |
| **Database performance issues** | Low | Medium | pgvector optimization, connection pooling, read replicas if needed |

---

## 8. Decision Log

### Key Technical Decisions

**Decision 1: Use Gemini embeddings instead of OpenAI** (✅ Implemented)
- **Rationale:** 50% cheaper, 2x faster, better for multilingual (RU+EN)
- **Trade-off:** Less accurate for English academic texts
- **Reversal cost:** Medium (need to regenerate all embeddings + schema migration)

**Decision 2: Use Claude 4.x exclusively (no GPT)** (✅ Implemented)
- **Rationale:** Better context window (200K), superior reasoning, better Russian support
- **Trade-off:** Slightly more expensive than GPT-3.5
- **Reversal cost:** Low (just change LLM service configuration)

**Decision 3: Build frontend after backend features** (⏳ In Progress)
- **Rationale:** Backend is more complex, faster to iterate, can test with curl/Postman
- **Trade-off:** No user testing until Week 7-8
- **Mitigation:** Use API documentation and mocks for early user feedback

**Decision 4: Defer Alerts and Reference Check to post-MVP** (⏳ Planned)
- **Rationale:** Lower user value, more complex, not blocking for first demo
- **Trade-off:** Missing 2 features from Elicit
- **Mitigation:** Focus on core workflow (search → collect → extract → format)

---

## 9. Next Steps (Immediate Actions)

### This Week (Week 2 Completion)

**Monday-Tuesday:**
- [ ] Complete Collections CRUD backend (2 days)
  - Write database migration
  - Implement all endpoints
  - Add tests
  - Update API documentation

**Wednesday:**
- [ ] Polish authentication (0.5 day)
  - Fix bugs
  - Improve error messages
  - Test edge cases
- [ ] Polish OpenAlex integration (0.5 day)
  - Add cursor pagination
  - Add more filters
  - Add retry logic

**Thursday-Friday:**
- [ ] Code review and bug fixes
- [ ] Integration testing
- [ ] Prepare for Phase 1 (Week 3-4)

### Next Week (Week 3-4: Collections + GOST)

**Goal:** Users can manage collections and format bibliographies

- [ ] GOST Formatter integration (2 days)
- [ ] Collection export functionality (1 day)
- [ ] Testing and polish (2 days)

---

## 10. Conclusion

LitFinder MVP is **~15% complete** with Feature 1 (Research Assistant) fully implemented and foundation infrastructure in place.

**Path to First Demo (8 weeks total):**
- ✅ Week 1-2: Foundation + Feature 1 (**70% complete**)
- ⏳ Week 3-4: Collections + GOST Formatter
- ⏳ Week 5-6: Data Extraction + Chat with Library
- ⏳ Week 7: Systematic Reviews + Concept Map
- ⏳ Week 8: Frontend MVP → **FIRST DEMO READY**

**Key Advantages Over Elicit:**
1. **GOST formatting** (VAK RB + GOST R) - unique for CIS market
2. **Russian language support** - native multilingual
3. **Cost-effective** - $1/user/month vs $10-50/user/month for Elicit
4. **Modern tech stack** - FastAPI + Next.js + Claude 4.x

**Critical Success Factors:**
- Complete Phase 1-4 on schedule (no delays)
- Maintain code quality (test coverage, security)
- Get early user feedback (pilot with BGU students)
- Control LLM costs (optimization, caching)

---

**Document Version:** 1.0
**Last Updated:** February 13, 2026
**Next Review:** End of Week 2 (Sprint retrospective)
